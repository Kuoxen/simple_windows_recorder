import ctypes
from ctypes import wintypes, POINTER, Structure, c_void_p, c_uint32, c_float, c_wchar_p, byref, c_int, c_short, c_ulong, c_long
import numpy as np
import threading
import time
import logging
import platform
from typing import Optional, List, Callable, Dict

# 定义HRESULT类型
HRESULT = c_long

# Windows COM 接口定义
class GUID(Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD), 
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8)
    ]

class WAVEFORMATEX(Structure):
    _fields_ = [
        ("wFormatTag", wintypes.WORD),
        ("nChannels", wintypes.WORD),
        ("nSamplesPerSec", wintypes.DWORD),
        ("nAvgBytesPerSec", wintypes.DWORD),
        ("nBlockAlign", wintypes.WORD),
        ("wBitsPerSample", wintypes.WORD),
        ("cbSize", wintypes.WORD)
    ]

# WASAPI GUID常量
IID_IMMDeviceEnumerator = GUID(0xa95664d2, 0x9614, 0x4f35, (0xa7, 0x46, 0xde, 0x8d, 0xb6, 0x36, 0x17, 0xe6))
CLSID_MMDeviceEnumerator = GUID(0xbcde0395, 0xe52f, 0x467c, (0x8e, 0x3d, 0xc4, 0x57, 0x92, 0x91, 0x69, 0x2e))
IID_IAudioClient = GUID(0x1cb9ad4c, 0xdbfa, 0x4c32, (0xb1, 0x78, 0xc2, 0xf5, 0x68, 0xa7, 0x03, 0xb2))
IID_IAudioCaptureClient = GUID(0xc8adbd64, 0xe71e, 0x48a0, (0xa4, 0xde, 0x18, 0x5c, 0x39, 0x5c, 0xd3, 0x17))

# 常量
AUDCLNT_SHAREMODE_SHARED = 0
AUDCLNT_STREAMFLAGS_LOOPBACK = 0x00020000
WAVE_FORMAT_PCM = 1
CLSCTX_ALL = 23

class WASAPIRecorder:
    """WASAPI Loopback录制器 - 直接录制系统音频输出"""
    
    BROWSER_PROCESSES = {'chrome.exe', 'firefox.exe', 'msedge.exe', 'opera.exe', 'brave.exe'}
    
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.logger = logging.getLogger(__name__)
        self._recording = False
        self._record_thread = None
        self._audio_callback: Optional[Callable[[np.ndarray], None]] = None
        
        # COM对象
        self._com_initialized = False
        self._device_enumerator = None
        self._device = None
        self._audio_client = None
        self._capture_client = None
        
        if platform.system() == "Windows":
            self._init_com()
    
    def _init_com(self):
        """初始化COM"""
        try:
            ctypes.windll.ole32.CoInitialize(None)
            self._com_initialized = True
            self.logger.info("COM初始化成功")
        except Exception as e:
            self.logger.error(f"COM初始化失败: {e}")
    
    def _init_wasapi_loopback(self) -> bool:
        """初始化WASAPI Loopback模式"""
        try:
            if platform.system() != "Windows":
                return False
            
            # 创建设备枚举器
            device_enumerator = ctypes.c_void_p()
            hr = ctypes.windll.ole32.CoCreateInstance(
                byref(CLSID_MMDeviceEnumerator),
                None,
                CLSCTX_ALL,
                byref(IID_IMMDeviceEnumerator),
                byref(device_enumerator)
            )
            
            if hr != 0:
                self.logger.error(f"创建设备枚举器失败: {hr}")
                return False
            
            self._device_enumerator = device_enumerator
            
            # 获取默认音频渲染设备 - 使用vtable调用
            device = ctypes.c_void_p()
            # IMMDeviceEnumerator::GetDefaultAudioEndpoint 在vtable中的位置是3
            get_default_endpoint = ctypes.WINFUNCTYPE(
                HRESULT,
                ctypes.c_void_p,  # this
                ctypes.c_int,     # dataFlow
                ctypes.c_int,     # role
                ctypes.POINTER(ctypes.c_void_p)  # ppEndpoint
            )(3, "GetDefaultAudioEndpoint")
            
            # 从vtable获取函数指针
            vtable = ctypes.cast(device_enumerator, ctypes.POINTER(ctypes.c_void_p)).contents
            vtable_array = ctypes.cast(vtable, ctypes.POINTER(ctypes.c_void_p * 10)).contents
            get_default_func = ctypes.cast(vtable_array[3], get_default_endpoint)
            
            hr = get_default_func(device_enumerator, 0, 0, byref(device))
            
            if hr != 0:
                self.logger.error(f"获取默认渲染设备失败: {hr}")
                return False
            
            self._device = device
            
            # 激活音频客户端 - 使用vtable调用
            audio_client = ctypes.c_void_p()
            # IMMDevice::Activate 在vtable中的位置是3
            activate_func_type = ctypes.WINFUNCTYPE(
                HRESULT,
                ctypes.c_void_p,  # this
                ctypes.POINTER(GUID),  # iid
                wintypes.DWORD,   # dwClsCtx
                ctypes.c_void_p,  # pActivationParams
                ctypes.POINTER(ctypes.c_void_p)  # ppInterface
            )
            
            device_vtable = ctypes.cast(device, ctypes.POINTER(ctypes.c_void_p)).contents
            device_vtable_array = ctypes.cast(device_vtable, ctypes.POINTER(ctypes.c_void_p * 10)).contents
            activate_func = ctypes.cast(device_vtable_array[3], activate_func_type)
            
            hr = activate_func(device, byref(IID_IAudioClient), CLSCTX_ALL, None, byref(audio_client))
            
            if hr != 0:
                self.logger.error(f"激活音频客户端失败: {hr}")
                return False
            
            self._audio_client = audio_client
            
            # 获取混合格式 - 使用vtable调用
            wave_format_ptr = ctypes.c_void_p()
            # IAudioClient::GetMixFormat 在vtable中的位置是8
            get_mix_format_type = ctypes.WINFUNCTYPE(
                HRESULT,
                ctypes.c_void_p,  # this
                ctypes.POINTER(ctypes.c_void_p)  # ppDeviceFormat
            )
            
            client_vtable = ctypes.cast(audio_client, ctypes.POINTER(ctypes.c_void_p)).contents
            client_vtable_array = ctypes.cast(client_vtable, ctypes.POINTER(ctypes.c_void_p * 20)).contents
            get_mix_format_func = ctypes.cast(client_vtable_array[8], get_mix_format_type)
            
            hr = get_mix_format_func(audio_client, byref(wave_format_ptr))
            
            if hr != 0:
                self.logger.error(f"获取混合格式失败: {hr}")
                return False
            
            # 初始化音频客户端（Loopback模式）- 使用vtable调用
            # IAudioClient::Initialize 在vtable中的位置是3
            initialize_type = ctypes.WINFUNCTYPE(
                HRESULT,
                ctypes.c_void_p,  # this
                ctypes.c_int,     # ShareMode
                wintypes.DWORD,   # StreamFlags
                ctypes.c_longlong,  # hnsBufferDuration
                ctypes.c_longlong,  # hnsPeriodicity
                ctypes.c_void_p,  # pFormat
                ctypes.c_void_p   # AudioSessionGuid
            )
            
            initialize_func = ctypes.cast(client_vtable_array[3], initialize_type)
            hr = initialize_func(
                audio_client,
                AUDCLNT_SHAREMODE_SHARED,
                AUDCLNT_STREAMFLAGS_LOOPBACK,
                10000000,  # 1秒缓冲
                0,
                wave_format_ptr,
                None
            )
            
            if hr != 0:
                self.logger.error(f"初始化音频客户端失败: {hr}")
                return False
            
            # 获取捕获客户端 - 使用vtable调用
            capture_client = ctypes.c_void_p()
            # IAudioClient::GetService 在vtable中的位置是14
            get_service_type = ctypes.WINFUNCTYPE(
                HRESULT,
                ctypes.c_void_p,  # this
                ctypes.POINTER(GUID),  # riid
                ctypes.POINTER(ctypes.c_void_p)  # ppv
            )
            
            get_service_func = ctypes.cast(client_vtable_array[14], get_service_type)
            hr = get_service_func(audio_client, byref(IID_IAudioCaptureClient), byref(capture_client))
            
            if hr != 0:
                self.logger.error(f"获取捕获客户端失败: {hr}")
                return False
            
            self._capture_client = capture_client
            
            self.logger.info("WASAPI Loopback初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"WASAPI Loopback初始化失败: {e}")
            return False
    
    def get_browser_sessions(self) -> List[Dict]:
        """获取浏览器进程"""
        sessions = []
        try:
            if platform.system() != "Windows":
                return sessions
            
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() in self.BROWSER_PROCESSES:
                        sessions.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'volume': 0.0
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.logger.error(f"获取浏览器会话失败: {e}")
        
        return sessions
    
    def set_audio_callback(self, callback: Callable[[np.ndarray], None]):
        """设置音频数据回调"""
        self._audio_callback = callback
    
    def start_recording(self) -> bool:
        """开始录制"""
        if self._recording:
            return False
        
        if platform.system() != "Windows":
            self.logger.warning(f"非Windows系统({platform.system()})，WASAPI录制不可用")
            return False
        
        # 初始化WASAPI Loopback
        if not self._init_wasapi_loopback():
            self.logger.error("WASAPI Loopback初始化失败")
            return False
        
        # 启动音频客户端 - 使用vtable调用
        try:
            # IAudioClient::Start 在vtable中的位置是5
            start_type = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p)
            client_vtable = ctypes.cast(self._audio_client, ctypes.POINTER(ctypes.c_void_p)).contents
            client_vtable_array = ctypes.cast(client_vtable, ctypes.POINTER(ctypes.c_void_p * 20)).contents
            start_func = ctypes.cast(client_vtable_array[5], start_type)
            
            hr = start_func(self._audio_client)
            if hr != 0:
                self.logger.error(f"启动音频客户端失败: {hr}")
                return False
        except Exception as e:
            self.logger.error(f"启动音频客户端异常: {e}")
            return False
        
        self._recording = True
        self._record_thread = threading.Thread(target=self._record_loop, name="WASAPILoopback")
        self._record_thread.start()
        
        self.logger.info("WASAPI Loopback录制开始")
        return True
    
    def stop_recording(self):
        """停止录制"""
        if not self._recording:
            return
        
        self._recording = False
        
        # 停止音频客户端 - 使用vtable调用
        if self._audio_client:
            try:
                # IAudioClient::Stop 在vtable中的位置是6
                stop_type = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p)
                client_vtable = ctypes.cast(self._audio_client, ctypes.POINTER(ctypes.c_void_p)).contents
                client_vtable_array = ctypes.cast(client_vtable, ctypes.POINTER(ctypes.c_void_p * 20)).contents
                stop_func = ctypes.cast(client_vtable_array[6], stop_type)
                stop_func(self._audio_client)
            except:
                pass
        
        if self._record_thread and self._record_thread.is_alive():
            self._record_thread.join(timeout=5.0)
        
        # 清理COM对象
        self._capture_client = None
        self._audio_client = None
        self._device = None
        self._device_enumerator = None
        
        self.logger.info("WASAPI Loopback录制停止")
    
    def _record_loop(self):
        """录制循环 - WASAPI Loopback音频捕获"""
        if not self._capture_client:
            self.logger.error("捕获客户端未初始化")
            return
        
        self.logger.info("开始WASAPI Loopback音频捕获")
        
        while self._recording:
            try:
                # 获取可用的音频包数量 - 使用vtable调用
                packet_length = ctypes.c_uint32()
                # IAudioCaptureClient::GetNextPacketSize 在vtable中的位置是4
                get_packet_size_type = ctypes.WINFUNCTYPE(
                    HRESULT,
                    ctypes.c_void_p,
                    ctypes.POINTER(ctypes.c_uint32)
                )
                
                capture_vtable = ctypes.cast(self._capture_client, ctypes.POINTER(ctypes.c_void_p)).contents
                capture_vtable_array = ctypes.cast(capture_vtable, ctypes.POINTER(ctypes.c_void_p * 10)).contents
                get_packet_size_func = ctypes.cast(capture_vtable_array[4], get_packet_size_type)
                
                hr = get_packet_size_func(self._capture_client, byref(packet_length))
                
                if hr != 0:
                    time.sleep(0.001)
                    continue
                
                if packet_length.value == 0:
                    time.sleep(0.001)
                    continue
                
                # 获取音频数据 - 使用vtable调用
                data_ptr = ctypes.POINTER(ctypes.c_byte)()
                num_frames = ctypes.c_uint32()
                flags = ctypes.c_uint32()
                
                # IAudioCaptureClient::GetBuffer 在vtable中的位置是3
                get_buffer_type = ctypes.WINFUNCTYPE(
                    HRESULT,
                    ctypes.c_void_p,
                    ctypes.POINTER(ctypes.POINTER(ctypes.c_byte)),
                    ctypes.POINTER(ctypes.c_uint32),
                    ctypes.POINTER(ctypes.c_uint32),
                    ctypes.c_void_p,
                    ctypes.c_void_p
                )
                
                get_buffer_func = ctypes.cast(capture_vtable_array[3], get_buffer_type)
                hr = get_buffer_func(
                    self._capture_client,
                    byref(data_ptr),
                    byref(num_frames),
                    byref(flags),
                    None,
                    None
                )
                
                if hr != 0 or num_frames.value == 0:
                    time.sleep(0.001)
                    continue
                
                # 转换音频数据
                try:
                    # 假设是16位立体声
                    bytes_per_frame = 4  # 2 channels * 2 bytes per sample
                    buffer_size = num_frames.value * bytes_per_frame
                    
                    if buffer_size > 0:
                        # 读取音频数据
                        audio_buffer = np.frombuffer(
                            ctypes.string_at(data_ptr, buffer_size),
                            dtype=np.int16
                        )
                        
                        # 转换为float32并归一化
                        if len(audio_buffer) > 0:
                            # 立体声转单声道
                            if len(audio_buffer) % 2 == 0:
                                left = audio_buffer[0::2].astype(np.float32) / 32768.0
                                right = audio_buffer[1::2].astype(np.float32) / 32768.0
                                audio_data = (left + right) / 2.0
                            else:
                                audio_data = audio_buffer.astype(np.float32) / 32768.0
                            
                            # 发送音频数据
                            if self._audio_callback:
                                self._audio_callback(audio_data)
                
                except Exception as e:
                    self.logger.error(f"音频数据处理错误: {e}")
                
                # 释放缓冲区 - 使用vtable调用
                # IAudioCaptureClient::ReleaseBuffer 在vtable中的位置是5
                release_buffer_type = ctypes.WINFUNCTYPE(
                    HRESULT,
                    ctypes.c_void_p,
                    ctypes.c_uint32
                )
                
                release_buffer_func = ctypes.cast(capture_vtable_array[5], release_buffer_type)
                release_buffer_func(self._capture_client, num_frames)
                
            except Exception as e:
                self.logger.error(f"录制循环错误: {e}")
                time.sleep(0.01)
    
    def __del__(self):
        """析构函数"""
        self.stop_recording()
        if self._com_initialized:
            try:
                ctypes.windll.ole32.CoUninitialize()
            except:
                pass