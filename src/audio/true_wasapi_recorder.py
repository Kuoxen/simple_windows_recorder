"""
真正的 WASAPI Loopback 录音器
使用 PyAudio 的 WASAPI 支持，可以录制任何输出设备
"""

import pyaudio
import numpy as np
import wave
import threading
import time
from datetime import datetime
import os

class TrueWASAPIRecorder:
    def __init__(self, settings):
        self.settings = settings
        self.is_recording = False
        self.mic_data = []
        self.system_data = []
        self.start_time = None
        self.pa = pyaudio.PyAudio()
        
    def get_wasapi_loopback_device(self):
        """获取 WASAPI loopback 设备"""
        for i in range(self.pa.get_device_count()):
            device_info = self.pa.get_device_info_by_index(i)
            # 查找 WASAPI loopback 设备
            if (device_info.get('hostApi') == self._get_wasapi_host_api() and
                'loopback' in device_info.get('name', '').lower()):
                return i
        return None
    
    def _get_wasapi_host_api(self):
        """获取 WASAPI host API 索引"""
        for i in range(self.pa.get_host_api_count()):
            host_api_info = self.pa.get_host_api_info_by_index(i)
            if 'wasapi' in host_api_info.get('name', '').lower():
                return i
        return None
    
    def print_wasapi_devices(self):
        """打印所有 WASAPI 设备"""
        wasapi_host = self._get_wasapi_host_api()
        if wasapi_host is None:
            print("未找到 WASAPI host API")
            return
            
        print("=== WASAPI 设备列表 ===")
        for i in range(self.pa.get_device_count()):
            device_info = self.pa.get_device_info_by_index(i)
            if device_info.get('hostApi') == wasapi_host:
                device_type = []
                if device_info.get('maxInputChannels', 0) > 0:
                    device_type.append("输入")
                if device_info.get('maxOutputChannels', 0) > 0:
                    device_type.append("输出")
                
                is_loopback = 'loopback' in device_info.get('name', '').lower()
                loopback_mark = " [LOOPBACK]" if is_loopback else ""
                
                print(f"[{i}] {device_info.get('name')} - {'/'.join(device_type)}{loopback_mark}")
    
    def start_recording(self, mic_device=None):
        """开始录音"""
        if self.is_recording:
            return False
            
        self.is_recording = True
        self.mic_data = []
        self.system_data = []
        self.start_time = datetime.now()
        
        # 创建输出目录
        os.makedirs(self.settings.recording['output_dir'], exist_ok=True)
        
        # 获取 WASAPI loopback 设备
        loopback_device = self.get_wasapi_loopback_device()
        
        print(f"麦克风设备: {mic_device if mic_device is not None else '默认'}")
        print(f"WASAPI Loopback 设备: {loopback_device}")
        
        if loopback_device is None:
            print("警告: 未找到 WASAPI loopback 设备")
        
        # 启动录音线程
        self.mic_thread = threading.Thread(target=self._record_mic, args=(mic_device,))
        self.system_thread = threading.Thread(target=self._record_system_wasapi, args=(loopback_device,))
        
        self.mic_thread.start()
        self.system_thread.start()
        
        return True
    
    def stop_recording(self):
        """停止录音"""
        if not self.is_recording:
            return None
            
        self.is_recording = False
        
        # 等待线程结束
        self.mic_thread.join()
        self.system_thread.join()
        
        # 保存文件
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        mic_file = self._save_audio(self.mic_data, f"mic_wasapi_{timestamp}.wav")
        system_file = self._save_audio(self.system_data, f"system_wasapi_{timestamp}.wav")
        
        return {
            'mic_file': mic_file,
            'system_file': system_file,
            'duration': len(self.mic_data) / self.settings.audio['sample_rate'] if self.mic_data else 0
        }
    
    def _record_mic(self, device=None):
        """录制麦克风（使用 sounddevice，因为它对麦克风录制很稳定）"""
        import sounddevice as sd
        
        def callback(indata, frames, time, status):
            if self.is_recording:
                self.mic_data.extend(indata[:, 0])
        
        try:
            with sd.InputStream(
                device=device,
                channels=1,
                samplerate=self.settings.audio['sample_rate'],
                callback=callback,
                blocksize=self.settings.audio['chunk_size']
            ):
                while self.is_recording:
                    time.sleep(0.1)
        except Exception as e:
            print(f"麦克风录音错误: {e}")
    
    def _record_system_wasapi(self, device=None):
        """使用 PyAudio WASAPI 录制系统音频"""
        if device is None:
            print("跳过系统音频录制：未找到 WASAPI loopback 设备")
            return
        
        try:
            stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.settings.audio['sample_rate'],
                input=True,
                input_device_index=device,
                frames_per_buffer=self.settings.audio['chunk_size']
            )
            
            print("开始 WASAPI 系统音频录制...")
            
            while self.is_recording:
                try:
                    data = stream.read(self.settings.audio['chunk_size'], exception_on_overflow=False)
                    # 转换为 float32
                    audio_data = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                    self.system_data.extend(audio_data)
                except Exception as e:
                    print(f"读取音频数据错误: {e}")
                    break
            
            stream.stop_stream()
            stream.close()
            
        except Exception as e:
            print(f"WASAPI 系统音频录制错误: {e}")
    
    def _save_audio(self, data, filename):
        """保存音频文件"""
        if not data:
            return None
            
        filepath = os.path.join(self.settings.recording['output_dir'], filename)
        
        with wave.open(filepath, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.settings.audio['sample_rate'])
            
            # 转换为 int16
            audio_data = np.array(data, dtype=np.float32)
            audio_data = (audio_data * 32767).astype(np.int16)
            wf.writeframes(audio_data.tobytes())
        
        return filepath
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, 'pa'):
            self.pa.terminate()