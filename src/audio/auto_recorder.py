import sounddevice as sd
import numpy as np
import wave
import threading
import time
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from enum import Enum

from .circular_buffer import CircularBuffer
from .activity_detector import AudioActivityDetector

class RecordingState(Enum):
    IDLE = "idle"
    MONITORING = "monitoring"
    RECORDING = "recording"
    STOPPING = "stopping"

class AutoAudioRecorder:
    """自动音频录制器"""
    
    def __init__(self, settings):
        self.settings = settings
        self.auto_config = settings.auto_recording
        
        # 状态管理
        self.state = RecordingState.IDLE
        self.is_monitoring = False
        
        # 设备配置
        self.mic_device = None
        self.system_device = None
        
        # 缓冲区
        sample_rate = settings.audio['sample_rate']
        buffer_duration = self.auto_config.get('buffer_duration', 30.0)
        self.mic_buffer = CircularBuffer(buffer_duration, sample_rate)
        self.system_buffer = CircularBuffer(buffer_duration, sample_rate)
        
        # 活动检测器
        self.activity_detector = AudioActivityDetector(self.auto_config)
        
        # 录制数据
        self.recording_mic_data = []
        self.recording_system_data = []
        self.recording_start_time = None
        
        # 线程管理
        self.monitor_thread = None
        self.mic_stream = None
        self.system_stream = None
        
        # 回调和日志
        self.status_callback: Optional[Callable[[str], None]] = None
        self.logger = logging.getLogger(__name__)
        
        # 通话信息
        self.call_info = {}
    
    def set_status_callback(self, callback: Callable[[str], None]):
        """设置状态回调函数"""
        self.status_callback = callback
    
    def _notify_status(self, message: str):
        """通知状态变化"""
        self.logger.info(message)
        if self.status_callback:
            self.status_callback(message)
    
    def set_devices(self, mic_device: Optional[int], system_device: Optional[int]):
        """设置录制设备"""
        self.mic_device = mic_device
        self.system_device = system_device
    
    def set_call_info(self, agent_phone: str = "", customer_name: str = "", customer_id: str = ""):
        """设置通话信息"""
        self.call_info = {
            'agent_phone': agent_phone,
            'customer_name': customer_name,
            'customer_id': customer_id
        }
    
    def start_monitoring(self) -> bool:
        """开始监听模式"""
        if self.is_monitoring:
            self._notify_status("监听已在进行中")
            return False
        
        if not self._validate_devices():
            return False
        
        self.is_monitoring = True
        self.state = RecordingState.MONITORING
        
        # 启动音频流
        try:
            self._start_audio_streams()
            
            # 启动监听线程
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop,
                name="AutoRecorderMonitor"
            )
            self.monitor_thread.start()
            
            self._notify_status("🔍 开始监听音频活动...")
            return True
            
        except Exception as e:
            self.logger.error(f"启动监听失败: {e}")
            self.is_monitoring = False
            self.state = RecordingState.IDLE
            return False
    
    def stop_monitoring(self):
        """停止监听模式"""
        if not self.is_monitoring:
            return
        
        self._notify_status("正在停止监听...")
        self.is_monitoring = False
        
        # 如果正在录制，先停止录制
        if self.state == RecordingState.RECORDING:
            self._stop_recording()
        
        # 停止音频流
        self._stop_audio_streams()
        
        # 等待监听线程结束
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        self.state = RecordingState.IDLE
        self._notify_status("监听已停止")
    
    def _validate_devices(self) -> bool:
        """验证设备是否可用"""
        try:
            devices = sd.query_devices()
            
            if self.mic_device is not None:
                if self.mic_device >= len(devices) or devices[self.mic_device]['max_input_channels'] == 0:
                    self._notify_status(f"❌ 无效的麦克风设备ID: {self.mic_device}")
                    return False
            
            if self.system_device is not None:
                if self.system_device >= len(devices) or devices[self.system_device]['max_input_channels'] == 0:
                    self._notify_status(f"❌ 无效的系统音频设备ID: {self.system_device}")
                    return False
            
            return True
        except Exception as e:
            self._notify_status(f"❌ 设备验证失败: {e}")
            return False
    
    def _start_audio_streams(self):
        """启动音频流"""
        sample_rate = self.settings.audio['sample_rate']
        chunk_size = self.settings.audio['chunk_size']
        
        self._notify_status(f"启动音频流 - 采样率:{sample_rate}, 块大小:{chunk_size}")
        
        # 麦克风流
        def mic_callback(indata, frames, time, status):
            if status:
                self.logger.warning(f"麦克风音频状态: {status}")
            
            if len(indata) > 0:
                audio_data = indata[:, 0] if indata.shape[1] > 0 else np.zeros(frames)
                
                # 写入缓冲区
                self.mic_buffer.write(audio_data)
                
                # 如果正在录制，也写入录制数据
                if self.state == RecordingState.RECORDING:
                    self.recording_mic_data.extend(audio_data)
                
                # 更新活动检测
                is_active = self.activity_detector.update_mic_activity(audio_data)
                
                # 每100次回调输出一次调试信息
                if hasattr(self, '_mic_callback_count'):
                    self._mic_callback_count += 1
                else:
                    self._mic_callback_count = 1
                
                if self._mic_callback_count % 100 == 0:
                    volume = np.max(np.abs(audio_data)) if len(audio_data) > 0 else 0
                    self.logger.debug(f"麦克风 #{self._mic_callback_count}: 音量={volume:.4f}, 活跃={is_active}")
        
        # 系统音频流
        def system_callback(indata, frames, time, status):
            if status:
                self.logger.warning(f"系统音频状态: {status}")
            
            if len(indata) > 0:
                audio_data = indata[:, 0] if indata.shape[1] > 0 else np.zeros(frames)
                
                # 写入缓冲区
                self.system_buffer.write(audio_data)
                
                # 如果正在录制，也写入录制数据
                if self.state == RecordingState.RECORDING:
                    self.recording_system_data.extend(audio_data)
                
                # 更新活动检测
                is_active = self.activity_detector.update_system_activity(audio_data)
                
                # 每100次回调输出一次调试信息
                if hasattr(self, '_system_callback_count'):
                    self._system_callback_count += 1
                else:
                    self._system_callback_count = 1
                
                if self._system_callback_count % 100 == 0:
                    volume = np.max(np.abs(audio_data)) if len(audio_data) > 0 else 0
                    self.logger.debug(f"系统音频 #{self._system_callback_count}: 音量={volume:.4f}, 活跃={is_active}")
        
        # 启动流
        self.mic_stream = sd.InputStream(
            device=self.mic_device,
            channels=1,
            samplerate=sample_rate,
            callback=mic_callback,
            blocksize=chunk_size,
            dtype=np.float32
        )
        
        self.system_stream = sd.InputStream(
            device=self.system_device,
            channels=1,
            samplerate=sample_rate,
            callback=system_callback,
            blocksize=chunk_size,
            dtype=np.float32
        )
        
        self.mic_stream.start()
        self.system_stream.start()
        
        self._notify_status(f"✅ 音频流已启动 - 麦克风设备:{self.mic_device}, 系统音频设备:{self.system_device}")
    
    def _stop_audio_streams(self):
        """停止音频流"""
        if self.mic_stream:
            self.mic_stream.stop()
            self.mic_stream.close()
            self.mic_stream = None
        
        if self.system_stream:
            self.system_stream.stop()
            self.system_stream.close()
            self.system_stream = None
    
    def _monitor_loop(self):
        """监听循环"""
        check_interval = self.auto_config.get('check_interval', 0.5)
        loop_count = 0
        
        self._notify_status(f"监听循环已启动，检查间隔: {check_interval}秒")
        
        while self.is_monitoring:
            try:
                loop_count += 1
                
                # 每10次循环输出一次状态
                if loop_count % 20 == 0:  # 10秒输出一次
                    status = self.activity_detector.get_status()
                    self._notify_status(f"监听状态: 麦克风活跃={status.get('mic_active', False)}, "
                                      f"系统音频活跃={status.get('system_active', False)}, "
                                      f"静默时长={status.get('silence_duration', 0):.1f}s, "
                                      f"麦克风活跃时长={status.get('mic_active_duration', 0):.1f}s, "
                                      f"系统音频活跃时长={status.get('system_active_duration', 0):.1f}s")
                
                if self.state == RecordingState.MONITORING:
                    # 检查是否应该开始录制
                    should_start = self.activity_detector.should_start_recording()
                    if should_start:
                        self._start_recording()
                    elif loop_count % 40 == 0:  # 每20秒输出一次检查结果
                        status = self.activity_detector.get_status()
                        self.logger.debug(f"检查开始录制: should_start={should_start}, 阈值={self.activity_detector.start_duration}s")
                
                elif self.state == RecordingState.RECORDING:
                    # 检查是否应该停止录制
                    should_stop = self.activity_detector.should_stop_recording()
                    if should_stop:
                        self._stop_recording()
                    elif loop_count % 10 == 0:  # 录制时每5秒输出一次检查结果
                        status = self.activity_detector.get_status()
                        self.logger.debug(f"检查停止录制: should_stop={should_stop}, 静默时长={status.get('silence_duration', 0):.1f}s, 阈值={self.activity_detector.end_silence_duration}s")
                
                time.sleep(check_interval)
                
            except Exception as e:
                self.logger.error(f"监听循环错误: {e}")
                time.sleep(1.0)
        
        self._notify_status("监听循环已退出")
    
    def _start_recording(self):
        """开始录制"""
        self.state = RecordingState.RECORDING
        self.recording_start_time = datetime.now()
        
        # 清空录制数据
        self.recording_mic_data = []
        self.recording_system_data = []
        
        # 将缓冲区数据添加到录制数据
        self.recording_mic_data.extend(self.mic_buffer.read_all())
        self.recording_system_data.extend(self.system_buffer.read_all())
        
        # 标记通话开始
        self.activity_detector.start_call()
        
        self._notify_status("🔴 自动开始录制通话")
    
    def _stop_recording(self):
        """停止录制"""
        if self.state != RecordingState.RECORDING:
            return
        
        self.state = RecordingState.STOPPING
        
        # 获取通话时长
        call_duration = self.activity_detector.end_call()
        
        # 检查最小通话时长
        min_duration = self.auto_config.get('min_call_duration', 5.0)
        if call_duration < min_duration:
            self._notify_status(f"⚠️ 通话时长过短({call_duration:.1f}s < {min_duration}s)，已丢弃")
            self.state = RecordingState.MONITORING
            return
        
        # 保存录制文件
        result = self._save_recording()
        
        if result and (result.get('mic_success') or result.get('system_success')):
            self._notify_status(f"✅ 通话录制完成，时长: {call_duration:.1f}秒")
        else:
            self._notify_status("❌ 录制保存失败")
        
        self.state = RecordingState.MONITORING
    
    def _save_recording(self) -> Optional[Dict[str, Any]]:
        """保存录制文件"""
        if not self.recording_start_time:
            return None
        
        # 创建输出目录
        os.makedirs(self.settings.recording['output_dir'], exist_ok=True)
        
        # 生成文件名
        timestamp = self.recording_start_time.strftime("%Y%m%d_%H%M%S")
        filename_parts = [timestamp]
        
        if self.call_info.get('agent_phone'):
            filename_parts.extend(['Agent', self.call_info['agent_phone']])
        if self.call_info.get('customer_name'):
            filename_parts.extend(['Customer', self.call_info['customer_name']])
        if self.call_info.get('customer_id'):
            filename_parts.extend(['ID', self.call_info['customer_id']])
        
        base_filename = '_'.join(filename_parts)
        
        self._notify_status(f"正在保存录音文件: {base_filename}")
        
        result = {
            'duration': (datetime.now() - self.recording_start_time).total_seconds(),
            'mic_file': None,
            'system_file': None,
            'mic_success': False,
            'system_success': False
        }
        
        # 保存麦克风录音
        if self.recording_mic_data:
            self._notify_status(f"保存麦克风数据: {len(self.recording_mic_data)} 个采样点")
            mic_file = self._save_audio_file(
                self.recording_mic_data, 
                f"mic_{base_filename}.wav"
            )
            if mic_file:
                result['mic_file'] = mic_file
                result['mic_success'] = True
                self._notify_status(f"✅ 麦克风文件保存成功: {os.path.basename(mic_file)}")
        else:
            self._notify_status("⚠️ 麦克风数据为空")
        
        # 保存系统音频录音
        if self.recording_system_data:
            self._notify_status(f"保存系统音频数据: {len(self.recording_system_data)} 个采样点")
            system_file = self._save_audio_file(
                self.recording_system_data, 
                f"system_{base_filename}.wav"
            )
            if system_file:
                result['system_file'] = system_file
                result['system_success'] = True
                self._notify_status(f"✅ 系统音频文件保存成功: {os.path.basename(system_file)}")
        else:
            self._notify_status("⚠️ 系统音频数据为空")
        
        return result
    
    def _save_audio_file(self, data: list, filename: str) -> Optional[str]:
        """保存音频文件"""
        if not data:
            return None
        
        filepath = os.path.join(self.settings.recording['output_dir'], filename)
        
        try:
            audio_data = np.array(data, dtype=np.float32)
            
            # 标准化
            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data)) * 0.95
            
            # 转换为16位整数
            audio_data_int16 = (audio_data * 32767).astype(np.int16)
            
            with wave.open(filepath, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.settings.audio['sample_rate'])
                wf.writeframes(audio_data_int16.tobytes())
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"保存音频文件失败: {filename}, 错误: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """获取录制器状态"""
        status = {
            'monitoring': self.is_monitoring,
            'state': self.state.value,
            'mic_device': self.mic_device,
            'system_device': self.system_device
        }
        
        if self.is_monitoring:
            detector_status = self.activity_detector.get_status()
            status.update(detector_status)
            
            if self.state == RecordingState.RECORDING and self.recording_start_time:
                status['recording_duration'] = (datetime.now() - self.recording_start_time).total_seconds()
        
        return status
    
    def update_config(self, key: str, value: Any):
        """更新配置"""
        if hasattr(self.activity_detector, key):
            setattr(self.activity_detector, key, value)
            self.settings.update_auto_recording(key, value)