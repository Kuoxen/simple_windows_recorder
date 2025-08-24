import numpy as np
import wave
import threading
import time
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from enum import Enum

from .wasapi_recorder import WASAPIRecorder
from .circular_buffer import CircularBuffer
from .activity_detector import AudioActivityDetector

class BrowserRecordingState(Enum):
    IDLE = "idle"
    MONITORING = "monitoring" 
    RECORDING = "recording"

class BrowserAudioRecorder:
    """浏览器音频录制器 - 只录制浏览器音频"""
    
    def __init__(self, settings):
        self.settings = settings
        self.auto_config = settings.auto_recording
        
        # 状态管理
        self.state = BrowserRecordingState.IDLE
        self.is_monitoring = False
        
        # WASAPI录制器
        self.wasapi_recorder = WASAPIRecorder(settings.audio['sample_rate'])
        self.wasapi_recorder.set_audio_callback(self._on_browser_audio)
        
        # 麦克风录制器 (仍使用sounddevice)
        import sounddevice as sd
        self.mic_device = None
        self.mic_stream = None
        
        # 缓冲区
        sample_rate = settings.audio['sample_rate']
        buffer_duration = self.auto_config.get('buffer_duration', 30.0)
        self.mic_buffer = CircularBuffer(buffer_duration, sample_rate)
        self.browser_buffer = CircularBuffer(buffer_duration, sample_rate)
        
        # 活动检测器 - 只检测浏览器音频
        self.activity_detector = AudioActivityDetector(self.auto_config)
        
        # 录制数据
        self.recording_mic_data = []
        self.recording_browser_data = []
        self.recording_start_time = None
        
        # 监控线程
        self.monitor_thread = None
        
        # 回调和日志
        self.status_callback: Optional[Callable[[str], None]] = None
        self.logger = logging.getLogger(__name__)
        
        # 通话信息
        self.call_info = {}
    
    def set_status_callback(self, callback: Callable[[str], None]):
        """设置状态回调"""
        self.status_callback = callback
    
    def _notify_status(self, message: str):
        """通知状态变化"""
        self.logger.info(message)
        if self.status_callback:
            self.status_callback(message)
    
    def set_devices(self, mic_device: Optional[int], system_device: Optional[int] = None):
        """设置录制设备 - system_device参数忽略，因为我们用WASAPI"""
        self.mic_device = mic_device
    
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
        
        self.is_monitoring = True
        self.state = BrowserRecordingState.MONITORING
        
        try:
            # 启动WASAPI录制器
            if not self.wasapi_recorder.start_recording():
                raise Exception("WASAPI录制器启动失败")
            
            # 启动麦克风流
            self._start_mic_stream()
            
            # 启动监听线程
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop,
                name="BrowserAudioMonitor"
            )
            self.monitor_thread.start()
            
            self._notify_status("🔍 开始监听浏览器音频活动...")
            return True
            
        except Exception as e:
            self.logger.error(f"启动监听失败: {e}")
            self.is_monitoring = False
            self.state = BrowserRecordingState.IDLE
            return False
    
    def stop_monitoring(self):
        """停止监听模式"""
        if not self.is_monitoring:
            return
        
        self._notify_status("正在停止监听...")
        self.is_monitoring = False
        
        # 如果正在录制，先停止录制
        if self.state == BrowserRecordingState.RECORDING:
            self._stop_recording()
        
        # 停止WASAPI录制器
        self.wasapi_recorder.stop_recording()
        
        # 停止麦克风流
        self._stop_mic_stream()
        
        # 等待监听线程结束
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        self.state = BrowserRecordingState.IDLE
        self._notify_status("监听已停止")
    
    def _start_mic_stream(self):
        """启动麦克风流"""
        if self.mic_device is None:
            return
        
        import sounddevice as sd
        
        def mic_callback(indata, frames, time, status):
            if status:
                self.logger.warning(f"麦克风音频状态: {status}")
            
            if len(indata) > 0:
                audio_data = indata[:, 0] if indata.shape[1] > 0 else np.zeros(frames)
                
                # 写入缓冲区
                self.mic_buffer.write(audio_data)
                
                # 如果正在录制，也写入录制数据
                if self.state == BrowserRecordingState.RECORDING:
                    self.recording_mic_data.extend(audio_data)
        
        self.mic_stream = sd.InputStream(
            device=self.mic_device,
            channels=1,
            samplerate=self.settings.audio['sample_rate'],
            callback=mic_callback,
            blocksize=self.settings.audio['chunk_size'],
            dtype=np.float32
        )
        self.mic_stream.start()
        self._notify_status(f"✅ 麦克风流已启动 - 设备:{self.mic_device}")
    
    def _stop_mic_stream(self):
        """停止麦克风流"""
        if self.mic_stream:
            self.mic_stream.stop()
            self.mic_stream.close()
            self.mic_stream = None
    
    def _on_browser_audio(self, audio_data: np.ndarray):
        """浏览器音频回调"""
        # 写入缓冲区
        self.browser_buffer.write(audio_data)
        
        # 如果正在录制，也写入录制数据
        if self.state == BrowserRecordingState.RECORDING:
            self.recording_browser_data.extend(audio_data)
        
        # 更新活动检测 - 只检测浏览器音频
        self.activity_detector.update_system_activity(audio_data)
    
    def _monitor_loop(self):
        """监听循环"""
        check_interval = self.auto_config.get('check_interval', 0.5)
        loop_count = 0
        
        while self.is_monitoring:
            try:
                loop_count += 1
                
                # 每20次循环输出一次状态
                if loop_count % 20 == 0:
                    browser_sessions = self.wasapi_recorder.get_browser_sessions()
                    self._notify_status(f"监听状态: 浏览器进程={len(browser_sessions)}")
                
                if self.state == BrowserRecordingState.MONITORING:
                    # 检查是否应该开始录制
                    if self.activity_detector.should_start_recording():
                        self._start_recording()
                
                elif self.state == BrowserRecordingState.RECORDING:
                    # 检查是否应该停止录制
                    if self.activity_detector.should_stop_recording():
                        self._stop_recording()
                
                time.sleep(check_interval)
                
            except Exception as e:
                self.logger.error(f"监听循环错误: {e}")
                time.sleep(1.0)
    
    def _start_recording(self):
        """开始录制"""
        self.state = BrowserRecordingState.RECORDING
        self.recording_start_time = datetime.now()
        
        # 清空录制数据
        self.recording_mic_data = []
        self.recording_browser_data = []
        
        # 将缓冲区数据添加到录制数据
        self.recording_mic_data.extend(self.mic_buffer.read_all())
        self.recording_browser_data.extend(self.browser_buffer.read_all())
        
        # 标记通话开始
        self.activity_detector.start_call()
        
        self._notify_status("🔴 检测到浏览器音频，自动开始录制通话")
    
    def _stop_recording(self):
        """停止录制"""
        if self.state != BrowserRecordingState.RECORDING:
            return
        
        # 获取通话时长
        call_duration = self.activity_detector.end_call()
        
        # 检查最小通话时长
        min_duration = self.auto_config.get('min_call_duration', 5.0)
        if call_duration < min_duration:
            self._notify_status(f"⚠️ 通话时长过短({call_duration:.1f}s < {min_duration}s)，已丢弃")
            self.state = BrowserRecordingState.MONITORING
            return
        
        # 保存录制文件
        result = self._save_recording()
        
        if result and (result.get('mic_success') or result.get('browser_success')):
            self._notify_status(f"✅ 浏览器通话录制完成，时长: {call_duration:.1f}秒")
        else:
            self._notify_status("❌ 录制保存失败")
        
        self.state = BrowserRecordingState.MONITORING
    
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
        
        result = {
            'duration': (datetime.now() - self.recording_start_time).total_seconds(),
            'mic_file': None,
            'browser_file': None,
            'mic_success': False,
            'browser_success': False
        }
        
        # 保存麦克风录音
        if self.recording_mic_data:
            mic_file = self._save_audio_file(
                self.recording_mic_data, 
                f"mic_{base_filename}.wav"
            )
            if mic_file:
                result['mic_file'] = mic_file
                result['mic_success'] = True
        
        # 保存浏览器音频录音
        if self.recording_browser_data:
            browser_file = self._save_audio_file(
                self.recording_browser_data, 
                f"browser_{base_filename}.wav"
            )
            if browser_file:
                result['browser_file'] = browser_file
                result['browser_success'] = True
        
        # 提交后处理
        if result.get('mic_success') or result.get('browser_success'):
            try:
                from .post_processor import AudioPostProcessor
                post_processor = AudioPostProcessor(self.settings)
                post_processor.submit_recording(
                    result.get('mic_file'),
                    result.get('browser_file'),
                    self.call_info
                )
            except Exception as e:
                self._notify_status(f"后处理提交失败: {e}")
        
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
            'browser_sessions': len(self.wasapi_recorder.get_browser_sessions())
        }
        
        if self.is_monitoring:
            detector_status = self.activity_detector.get_status()
            status.update(detector_status)
            
            if self.state == BrowserRecordingState.RECORDING and self.recording_start_time:
                status['recording_duration'] = (datetime.now() - self.recording_start_time).total_seconds()
        
        return status
    
    def update_config(self, key: str, value: Any):
        """更新配置"""
        if hasattr(self.activity_detector, key):
            setattr(self.activity_detector, key, value)
            self.settings.update_auto_recording(key, value)