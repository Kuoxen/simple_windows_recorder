import sounddevice as sd
import numpy as np
import wave
import threading
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Callable
import os

class EnhancedAudioRecorder:
    """增强版音频录制器，提供更稳定的录音功能和错误处理"""
    
    def __init__(self, settings):
        self.settings = settings
        self.is_recording = False
        self.mic_data = []
        self.speaker_data = []
        self.start_time = None
        self.logger = logging.getLogger(__name__)
        
        # 录音线程
        self.mic_thread = None
        self.speaker_thread = None
        
        # 错误处理
        self.mic_error = None
        self.speaker_error = None
        
        # 回调函数
        self.status_callback: Optional[Callable[[str], None]] = None
        
    def set_status_callback(self, callback: Callable[[str], None]):
        """设置状态回调函数"""
        self.status_callback = callback
        
    def _notify_status(self, message: str):
        """通知状态变化"""
        self.logger.info(message)
        if self.status_callback:
            self.status_callback(message)
    
    def start_recording(self, mic_device: Optional[int] = None, speaker_device: Optional[int] = None) -> bool:
        """开始录音"""
        if self.is_recording:
            self._notify_status("录音已在进行中")
            return False
        
        # 重置状态
        self.is_recording = True
        self.mic_data = []
        self.speaker_data = []
        self.mic_error = None
        self.speaker_error = None
        self.start_time = datetime.now()
        
        # 创建输出目录
        os.makedirs(self.settings.recording['output_dir'], exist_ok=True)
        
        # 验证设备
        if not self._validate_devices(mic_device, speaker_device):
            self.is_recording = False
            return False
        
        self._notify_status(f"开始录音 - 麦克风设备: {mic_device}, 系统音频设备: {speaker_device}")
        
        # 启动录音线程
        self.mic_thread = threading.Thread(
            target=self._record_microphone, 
            args=(mic_device,),
            name="MicrophoneRecorder"
        )
        self.speaker_thread = threading.Thread(
            target=self._record_system_audio, 
            args=(speaker_device,),
            name="SystemAudioRecorder"
        )
        
        try:
            self.mic_thread.start()
            self.speaker_thread.start()
            self._notify_status("录音线程已启动")
            return True
        except Exception as e:
            self.logger.error(f"启动录音线程失败: {e}")
            self.is_recording = False
            return False
    
    def stop_recording(self) -> Optional[Dict[str, Any]]:
        """停止录音"""
        if not self.is_recording:
            self._notify_status("当前没有进行录音")
            return None
        
        self._notify_status("正在停止录音...")
        self.is_recording = False
        
        # 等待线程结束
        if self.mic_thread and self.mic_thread.is_alive():
            self.mic_thread.join(timeout=5.0)
        if self.speaker_thread and self.speaker_thread.is_alive():
            self.speaker_thread.join(timeout=5.0)
        
        # 检查录音结果
        duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        # 保存文件
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S") if self.start_time else datetime.now().strftime("%Y%m%d_%H%M%S")
        
        result = {
            'duration': duration,
            'mic_file': None,
            'speaker_file': None,
            'mic_success': False,
            'speaker_success': False,
            'errors': []
        }
        
        # 处理麦克风录音
        if self.mic_error:
            result['errors'].append(f"麦克风录音错误: {self.mic_error}")
            self._notify_status(f"⚠️ 麦克风录音失败: {self.mic_error}")
        elif self.mic_data:
            mic_file = self._save_audio(self.mic_data, f"mic_{timestamp}.wav")
            if mic_file:
                result['mic_file'] = mic_file
                result['mic_success'] = True
                self._notify_status(f"✅ 麦克风录音保存成功: {os.path.basename(mic_file)}")
            else:
                result['errors'].append("麦克风音频保存失败")
        else:
            result['errors'].append("麦克风未录制到音频数据")
            self._notify_status("⚠️ 麦克风未录制到音频数据")
        
        # 处理系统音频录音
        if self.speaker_error:
            result['errors'].append(f"系统音频录音错误: {self.speaker_error}")
            self._notify_status(f"⚠️ 系统音频录音失败: {self.speaker_error}")
        elif self.speaker_data:
            speaker_file = self._save_audio(self.speaker_data, f"speaker_{timestamp}.wav")
            if speaker_file:
                result['speaker_file'] = speaker_file
                result['speaker_success'] = True
                self._notify_status(f"✅ 系统音频录音保存成功: {os.path.basename(speaker_file)}")
            else:
                result['errors'].append("系统音频保存失败")
        else:
            result['errors'].append("系统音频未录制到音频数据")
            self._notify_status("⚠️ 系统音频未录制到音频数据 - 请检查设备设置")
        
        self._notify_status(f"录音完成，总时长: {duration:.2f} 秒")
        return result
    
    def _validate_devices(self, mic_device: Optional[int], speaker_device: Optional[int]) -> bool:
        """验证设备是否可用"""
        try:
            devices = sd.query_devices()
            
            # 验证麦克风设备
            if mic_device is not None:
                if mic_device >= len(devices) or devices[mic_device]['max_input_channels'] == 0:
                    self._notify_status(f"❌ 无效的麦克风设备ID: {mic_device}")
                    return False
            
            # 验证系统音频设备
            if speaker_device is not None:
                if speaker_device >= len(devices) or devices[speaker_device]['max_input_channels'] == 0:
                    self._notify_status(f"❌ 无效的系统音频设备ID: {speaker_device}")
                    return False
            
            return True
        except Exception as e:
            self._notify_status(f"❌ 设备验证失败: {e}")
            return False
    
    def _record_microphone(self, device: Optional[int]):
        """录制麦克风音频"""
        try:
            self._notify_status("🎤 开始麦克风录音")
            
            def callback(indata, frames, time, status):
                if status:
                    self.logger.warning(f"麦克风录音状态警告: {status}")
                if self.is_recording and len(indata) > 0:
                    # 转换为单声道
                    if indata.shape[1] > 1:
                        audio_data = np.mean(indata, axis=1)
                    else:
                        audio_data = indata[:, 0]
                    self.mic_data.extend(audio_data)
            
            with sd.InputStream(
                device=device,
                channels=1,
                samplerate=self.settings.audio['sample_rate'],
                callback=callback,
                blocksize=self.settings.audio['chunk_size'],
                dtype=np.float32
            ) as stream:
                self._notify_status(f"🎤 麦克风录音流已启动 (设备: {device})")
                while self.is_recording:
                    time.sleep(0.1)
                    
        except Exception as e:
            self.mic_error = str(e)
            self.logger.error(f"麦克风录音错误: {e}")
        finally:
            self._notify_status("🎤 麦克风录音线程结束")
    
    def _record_system_audio(self, device: Optional[int]):
        """录制系统音频"""
        try:
            self._notify_status("🔊 开始系统音频录音")
            callback_count = 0
            data_received = 0
            
            def callback(indata, frames, time, status):
                nonlocal callback_count, data_received
                callback_count += 1
                
                if status:
                    self.logger.warning(f"系统音频录音状态警告: {status}")
                
                if self.is_recording and len(indata) > 0:
                    # 转换为单声道
                    if indata.shape[1] > 1:
                        audio_data = np.mean(indata, axis=1)
                    else:
                        audio_data = indata[:, 0]
                    
                    self.speaker_data.extend(audio_data)
                    data_received += len(audio_data)
                    
                    # 每100次回调输出一次调试信息
                    if callback_count % 100 == 0:
                        volume = np.max(np.abs(audio_data)) if len(audio_data) > 0 else 0
                        self.logger.debug(f"系统音频 callback #{callback_count}, 音量: {volume:.4f}, 总数据: {data_received}")
            
            with sd.InputStream(
                device=device,
                channels=1,
                samplerate=self.settings.audio['sample_rate'],
                callback=callback,
                blocksize=self.settings.audio['chunk_size'],
                dtype=np.float32
            ) as stream:
                self._notify_status(f"🔊 系统音频录音流已启动 (设备: {device})")
                while self.is_recording:
                    time.sleep(0.1)
                
                self._notify_status(f"🔊 系统音频录音完成，总回调: {callback_count}, 总数据: {data_received}")
                    
        except Exception as e:
            self.speaker_error = str(e)
            self.logger.error(f"系统音频录音错误: {e}")
        finally:
            self._notify_status("🔊 系统音频录音线程结束")
    
    def _save_audio(self, data: list, filename: str) -> Optional[str]:
        """保存音频文件"""
        if not data:
            self.logger.warning(f"音频数据为空，无法保存文件: {filename}")
            return None
        
        filepath = os.path.join(self.settings.recording['output_dir'], filename)
        
        try:
            # 转换数据格式
            audio_data = np.array(data, dtype=np.float32)
            
            # 标准化音频数据
            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data)) * 0.95
            
            # 转换为16位整数
            audio_data_int16 = (audio_data * 32767).astype(np.int16)
            
            with wave.open(filepath, 'wb') as wf:
                wf.setnchannels(1)  # 单声道
                wf.setsampwidth(2)  # 16位
                wf.setframerate(self.settings.audio['sample_rate'])
                wf.writeframes(audio_data_int16.tobytes())
            
            file_size = os.path.getsize(filepath)
            self.logger.info(f"音频文件保存成功: {filepath}, 大小: {file_size} 字节, 时长: {len(data)/self.settings.audio['sample_rate']:.2f}秒")
            return filepath
            
        except Exception as e:
            self.logger.error(f"保存音频文件失败: {filename}, 错误: {e}")
            return None
    
    def get_recording_status(self) -> Dict[str, Any]:
        """获取录音状态"""
        if not self.is_recording:
            return {'recording': False}
        
        duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        return {
            'recording': True,
            'duration': duration,
            'mic_data_length': len(self.mic_data),
            'speaker_data_length': len(self.speaker_data),
            'mic_error': self.mic_error,
            'speaker_error': self.speaker_error
        }