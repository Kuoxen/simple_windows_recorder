import numpy as np
import threading
import time
import logging
import platform
from typing import Optional, Callable, Dict, Any
from datetime import datetime

class EnhancedWASAPIRecorder:
    """增强的音频录制器 - 支持WASAPI Loopback + sounddevice fallback"""
    
    def __init__(self, settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # 录制状态
        self._recording = False
        self._record_thread = None
        self._audio_callback: Optional[Callable[[np.ndarray], None]] = None
        
        # 音频捕获方式
        self._capture_method = None  # 'pyaudio', 'wasapi', 'sounddevice', 'mic_only'
        self._stream = None
        self._pyaudio_recorder = None
        
        # 设备信息
        self.mic_device = None
        self.system_device = None
        
        # 录制数据
        self.recording_mic_data = []
        self.recording_system_data = []
        self.recording_start_time = None
        
    def set_status_callback(self, callback: Callable[[str], None]):
        """设置状态回调"""
        self.status_callback = callback
    
    def _notify_status(self, message: str):
        """通知状态变化"""
        self.logger.info(message)
        if hasattr(self, 'status_callback') and self.status_callback:
            self.status_callback(message)
    
    def set_devices(self, mic_device: Optional[int], system_device: Optional[int]):
        """设置录制设备"""
        self.mic_device = mic_device
        self.system_device = system_device
    
    def _init_wasapi_loopback(self) -> bool:
        """尝试初始化WASAPI Loopback"""
        try:
            if platform.system() != "Windows":
                return False
            
            # 使用sounddevice实现WASAPI Loopback效果
            import sounddevice as sd
            
            # 查找默认输出设备，尝试作为loopback使用
            devices = sd.query_devices()
            default_output = sd.default.device[1]
            
            if default_output is not None and default_output < len(devices):
                output_device = devices[default_output]
                self._notify_status(f"尝试WASAPI Loopback模式 - 目标设备: {output_device['name']}")
                
                # 检查是否有对应的loopback输入
                for i, device in enumerate(devices):
                    name = device['name'].lower()
                    # 查找与输出设备相关的loopback
                    if ('loopback' in name or 'mix' in name) and device['max_input_channels'] > 0:
                        self._system_loopback_device = i
                        self._notify_status(f"找到WASAPI Loopback设备: {device['name']}")
                        return True
                
                # 如果没有找到专用loopback，尝试使用默认输入作为系统音频
                if devices[default_output]['max_input_channels'] > 0:
                    self._system_loopback_device = default_output
                    self._notify_status(f"使用默认设备作为Loopback: {output_device['name']}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"WASAPI Loopback初始化失败: {e}")
            return False
    
    def _init_sounddevice_fallback(self) -> bool:
        """Fallback到sounddevice查找立体声混音"""
        try:
            import sounddevice as sd
            
            devices = sd.query_devices()
            
            # 查找立体声混音设备
            for i, device in enumerate(devices):
                name = device['name'].lower()
                stereo_mix_keywords = [
                    'stereo mix', 'stereo input', '立体声混音', 'what u hear', 
                    'wave out mix', 'loopback', 'mix'
                ]
                
                if any(keyword in name for keyword in stereo_mix_keywords):
                    if device['max_input_channels'] > 0:
                        self._system_loopback_device = i
                        self._notify_status(f"找到立体声混音设备: {device['name']}")
                        self._notify_status("⚠️ 使用立体声混音模式，需要在系统中手动开启")
                        return True
            
            self._notify_status("❌ 未找到立体声混音设备，请在声音设置中开启")
            return False
            
        except Exception as e:
            self.logger.error(f"sounddevice fallback失败: {e}")
            return False
    
    def start_recording(self, mic_device: Optional[int], system_device: Optional[int]) -> bool:
        """开始录制 - 自动选择最佳捕获方式"""
        if self._recording:
            return False
        
        self.set_devices(mic_device, system_device)
        
        # 尝试不同的音频捕获方式
        capture_success = False
        
        # 1. 优先尝试 PyAudioWPatch WASAPI loopback（无需立体声混音/虚拟声卡）
        if platform.system() == "Windows" and not capture_success:
            try:
                from audio.pyaudio_wasapi_recorder import PyaudioWasapiLoopbackRecorder
                self._pyaudio_recorder = PyaudioWasapiLoopbackRecorder(
                    sample_rate=self.settings.audio['sample_rate'],
                    channels=2
                )
                def on_system_audio(chunk: np.ndarray):
                    if self._recording and len(chunk) > 0:
                        self.recording_system_data.extend(chunk.astype(np.float32))
                self._pyaudio_recorder.set_audio_callback(on_system_audio)
                if self._pyaudio_recorder.start_recording():
                    self._capture_method = 'pyaudio'
                    capture_success = True
                    self._notify_status("✅ 使用WASAPI Loopback (PyAudioWPatch)")
                else:
                    self._pyaudio_recorder = None
            except Exception as e:
                self.logger.error(f"PyAudioWPatch 初始化失败: {e}")
                self._pyaudio_recorder = None

        # 2. 次优尝试 sounddevice 的“WASAPI-like”方案
        if platform.system() == "Windows" and not capture_success:
            if self._init_wasapi_loopback():
                capture_success = self._start_wasapi_capture()
                if capture_success:
                    self._capture_method = 'wasapi'
                    self._notify_status("✅ 使用WASAPI Loopback (sounddevice)")
        
        # 3. Fallback到sounddevice立体声混音
        if not capture_success:
            if self._init_sounddevice_fallback():
                capture_success = self._start_sounddevice_capture()
                if capture_success:
                    self._capture_method = 'sounddevice'
        
        # 4. 最后fallback到纯麦克风模式
        if not capture_success:
            capture_success = self._start_mic_only_capture()
            if capture_success:
                self._capture_method = 'mic_only'
                self._notify_status("⚠️ 仅麦克风模式 - 无法录制系统音频")
        
        if capture_success:
            self._recording = True
            self.recording_start_time = datetime.now()
            self._notify_status(f"录制开始 - 模式: {self._capture_method}")
            return True
        else:
            self._notify_status("❌ 所有音频捕获方式都失败")
            return False
    
    def _start_wasapi_capture(self) -> bool:
        """启动WASAPI捕获"""
        try:
            import sounddevice as sd
            
            def audio_callback(indata, frames, time, status):
                if status:
                    self.logger.warning(f"WASAPI音频状态: {status}")
                
                if self._recording and len(indata) > 0:
                    # 处理系统音频
                    if indata.shape[1] > 1:
                        system_audio = np.mean(indata, axis=1).astype(np.float32)
                    else:
                        system_audio = indata[:, 0].astype(np.float32)
                    
                    self.recording_system_data.extend(system_audio)
            
            # 启动系统音频流
            self._stream = sd.InputStream(
                device=self._system_loopback_device,
                channels=2,
                samplerate=self.settings.audio['sample_rate'],
                callback=audio_callback,
                blocksize=self.settings.audio['chunk_size'],
                dtype=np.float32
            )
            
            self._stream.start()
            
            # 启动麦克风流（当选择了具体麦克风设备时）
            if self.mic_device is not None and self.mic_device >= 0:
                self._start_mic_stream()
            
            return True
            
        except Exception as e:
            self.logger.error(f"WASAPI捕获启动失败: {e}")
            return False
    
    def _start_sounddevice_capture(self) -> bool:
        """启动sounddevice捕获"""
        try:
            import sounddevice as sd
            
            def audio_callback(indata, frames, time, status):
                if status:
                    self.logger.warning(f"立体声混音状态: {status}")
                
                if self._recording and len(indata) > 0:
                    # 处理系统音频
                    if indata.shape[1] > 1:
                        system_audio = np.mean(indata, axis=1).astype(np.float32)
                    else:
                        system_audio = indata[:, 0].astype(np.float32)
                    
                    self.recording_system_data.extend(system_audio)
            
            # 启动立体声混音流
            self._stream = sd.InputStream(
                device=self._system_loopback_device,
                channels=2,
                samplerate=self.settings.audio['sample_rate'],
                callback=audio_callback,
                blocksize=self.settings.audio['chunk_size'],
                dtype=np.float32
            )
            
            self._stream.start()
            
            # 启动麦克风流（当选择了具体麦克风设备时）
            if self.mic_device is not None and self.mic_device >= 0:
                self._start_mic_stream()
            
            return True
            
        except Exception as e:
            self.logger.error(f"立体声混音捕获启动失败: {e}")
            return False
    
    def _start_mic_only_capture(self) -> bool:
        """启动纯麦克风捕获"""
        try:
            if self.mic_device is not None:
                self._start_mic_stream()
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"麦克风捕获启动失败: {e}")
            return False
    
    def _start_mic_stream(self):
        """启动麦克风流"""
        try:
            import sounddevice as sd
            
            def mic_callback(indata, frames, time, status):
                if status:
                    self.logger.warning(f"麦克风状态: {status}")
                
                if self._recording and len(indata) > 0:
                    audio_data = indata[:, 0] if indata.shape[1] > 0 else np.zeros(frames)
                    self.recording_mic_data.extend(audio_data)
            
            self._mic_stream = sd.InputStream(
                device=self.mic_device,
                channels=1,
                samplerate=self.settings.audio['sample_rate'],
                callback=mic_callback,
                blocksize=self.settings.audio['chunk_size'],
                dtype=np.float32
            )
            
            self._mic_stream.start()
            self._notify_status(f"✅ 麦克风流已启动 - 设备:{self.mic_device}")
            
        except Exception as e:
            self.logger.error(f"麦克风流启动失败: {e}")
    
    def stop_recording(self) -> Optional[Dict[str, Any]]:
        """停止录制"""
        if not self._recording:
            return None
        
        self._recording = False
        
        # 停止音频流
        if hasattr(self, '_stream') and self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except:
                pass
        
        # 停止 PyAudioWPatch 录制
        if self._pyaudio_recorder:
            try:
                self._pyaudio_recorder.stop_recording()
            except:
                pass
            finally:
                self._pyaudio_recorder = None

        if hasattr(self, '_mic_stream') and self._mic_stream:
            try:
                self._mic_stream.stop()
                self._mic_stream.close()
            except:
                pass
        
        # 计算录制时长
        duration = (datetime.now() - self.recording_start_time).total_seconds() if self.recording_start_time else 0
        
        self._notify_status(f"录制停止 - 时长: {duration:.2f}秒, 模式: {self._capture_method}")
        
        return {
            'duration': duration,
            'mic_data': self.recording_mic_data.copy(),
            'system_data': self.recording_system_data.copy(),
            'capture_method': self._capture_method
        }
    
    def get_recording_status(self) -> Dict[str, Any]:
        """获取录制状态"""
        if not self._recording or not self.recording_start_time:
            return {'recording': False, 'duration': 0}
        
        duration = (datetime.now() - self.recording_start_time).total_seconds()
        return {
            'recording': True,
            'duration': duration,
            'capture_method': self._capture_method
        }