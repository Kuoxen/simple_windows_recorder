import ctypes
from ctypes import wintypes, POINTER, Structure, c_void_p, c_uint32, c_float, c_wchar_p, byref
import numpy as np
import threading
import time
import logging
from typing import Optional, List, Callable, Dict

# Windows COM 接口定义
class GUID(Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD), 
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8)
    ]

# 重要的GUID常量
IID_IMMDeviceEnumerator = GUID(0xa95664d2, 0x9614, 0x4f35, (0xa7, 0x46, 0xde, 0x8d, 0xb6, 0x36, 0x17, 0xe6))
CLSID_MMDeviceEnumerator = GUID(0xbcde0395, 0xe52f, 0x467c, (0x8e, 0x3d, 0xc4, 0x57, 0x92, 0x91, 0x69, 0x2e))
IID_IAudioSessionManager2 = GUID(0x77aa99a0, 0x1bd6, 0x484f, (0x8b, 0xc7, 0x2c, 0x65, 0x4c, 0x9a, 0x9b, 0x6f))
IID_IAudioSessionEnumerator = GUID(0xe2f5bb11, 0x0570, 0x40ca, (0xac, 0xdd, 0x3a, 0xa0, 0x12, 0x77, 0xde, 0xe8))
IID_IAudioSessionControl = GUID(0xf4b1a599, 0x7266, 0x4319, (0xa8, 0xca, 0xe7, 0x0a, 0xcb, 0x11, 0xe8, 0xcd))
IID_IAudioSessionControl2 = GUID(0xbfb7ff88, 0x7239, 0x4fc9, (0x8f, 0xa2, 0x07, 0xc9, 0x50, 0xbe, 0x9c, 0x6d))
IID_ISimpleAudioVolume = GUID(0x87ce5498, 0x68d6, 0x44e5, (0x92, 0x15, 0x6d, 0xa4, 0x7e, 0xf8, 0x83, 0xd8))

class WASAPIRecorder:
    """WASAPI音频录制器 - 可以录制特定进程的音频"""
    
    BROWSER_PROCESSES = {'chrome.exe', 'firefox.exe', 'msedge.exe', 'opera.exe', 'brave.exe'}
    
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.logger = logging.getLogger(__name__)
        self._recording = False
        self._record_thread = None
        self._audio_callback: Optional[Callable[[np.ndarray], None]] = None
        
        # COM初始化
        self._com_initialized = False
        self._init_com()
    
    def _init_com(self):
        """初始化COM"""
        try:
            ctypes.windll.ole32.CoInitialize(None)
            self._com_initialized = True
            self.logger.info("COM初始化成功")
        except Exception as e:
            self.logger.error(f"COM初始化失败: {e}")
    
    def get_browser_sessions(self) -> List[Dict]:
        """获取浏览器音频会话"""
        sessions = []
        try:
            # 使用psutil简化实现
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() in self.BROWSER_PROCESSES:
                        sessions.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'volume': 0.0  # 实际需要通过WASAPI获取
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.logger.error(f"获取浏览器会话失败: {e}")
        
        return sessions
    
    def has_active_browser_audio(self) -> bool:
        """检查是否有活跃的浏览器音频"""
        sessions = self.get_browser_sessions()
        return len(sessions) > 0  # 简化实现
    
    def set_audio_callback(self, callback: Callable[[np.ndarray], None]):
        """设置音频数据回调"""
        self._audio_callback = callback
    
    def start_recording(self) -> bool:
        """开始录制"""
        if self._recording:
            return False
        
        self._recording = True
        self._record_thread = threading.Thread(target=self._record_loop, name="WASAPIRecorder")
        self._record_thread.start()
        
        self.logger.info("WASAPI录制开始")
        return True
    
    def stop_recording(self):
        """停止录制"""
        if not self._recording:
            return
        
        self._recording = False
        if self._record_thread and self._record_thread.is_alive():
            self._record_thread.join(timeout=5.0)
        
        self.logger.info("WASAPI录制停止")
    
    def _record_loop(self):
        """录制循环 - 简化版本，实际需要调用WASAPI"""
        chunk_size = 1024
        
        while self._recording:
            try:
                # 模拟音频数据 - 实际需要从WASAPI获取
                if self.has_active_browser_audio():
                    # 生成模拟数据
                    audio_data = np.random.normal(0, 0.01, chunk_size).astype(np.float32)
                else:
                    # 静音
                    audio_data = np.zeros(chunk_size, dtype=np.float32)
                
                if self._audio_callback:
                    self._audio_callback(audio_data)
                
                time.sleep(chunk_size / self.sample_rate)
                
            except Exception as e:
                self.logger.error(f"录制循环错误: {e}")
                time.sleep(0.1)
    
    def __del__(self):
        """析构函数"""
        self.stop_recording()
        if self._com_initialized:
            try:
                ctypes.windll.ole32.CoUninitialize()
            except:
                pass