"""
Windows WASAPI 录音器
支持录制任何输出设备的音频，包括蓝牙耳机
"""

import sounddevice as sd
import numpy as np
import threading
import time
from datetime import datetime
import os
import wave

class WASAPIRecorder:
    def __init__(self, settings):
        self.settings = settings
        self.is_recording = False
        self.mic_data = []
        self.system_data = []
        self.start_time = None
        
    def get_default_output_as_input(self):
        """获取默认输出设备对应的loopback输入"""
        devices = sd.query_devices()
        default_output = sd.default.device[1]
        
        # 查找对应的loopback设备
        if default_output is not None:
            output_device = devices[default_output]
            output_name = output_device['name'].lower()
            
            # 尝试找到对应的输入设备
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    device_name = device['name'].lower()
                    # 检查是否是同一设备的输入版本
                    if any(keyword in device_name for keyword in [
                        'loopback', 'stereo mix', 'what u hear',
                        '立体声混音', '混音'
                    ]):
                        return i
                    
                    # 或者设备名相似（蓝牙设备可能有输入版本）
                    if self._is_same_device(output_name, device_name):
                        return i
        
        return None
    
    def _is_same_device(self, output_name, input_name):
        """判断是否是同一设备的输入输出版本"""
        # 提取设备的核心名称
        output_core = self._extract_device_core(output_name)
        input_core = self._extract_device_core(input_name)
        
        return output_core == input_core and output_core != ""
    
    def _extract_device_core(self, device_name):
        """提取设备核心名称"""
        # 移除常见的前后缀
        name = device_name.lower()
        prefixes = ['麦克风', 'microphone', 'speakers', '扬声器', '耳机', 'headphone']
        suffixes = ['input', 'output', 'loopback']
        
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):].strip()
                break
                
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)].strip()
                break
        
        # 提取品牌名或型号
        if '(' in name and ')' in name:
            return name[name.find('(')+1:name.find(')')].strip()
        
        return name.strip()
    
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
        
        # 获取系统音频设备
        system_device = self.get_default_output_as_input()
        
        print(f"麦克风设备: {mic_device if mic_device is not None else '默认'}")
        print(f"系统音频设备: {system_device}")
        
        if system_device is None:
            print("警告: 无法找到系统音频录制设备")
        
        # 启动录音线程
        self.mic_thread = threading.Thread(target=self._record_mic, args=(mic_device,))
        self.system_thread = threading.Thread(target=self._record_system, args=(system_device,))
        
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
        mic_file = self._save_audio(self.mic_data, f"mic_{timestamp}.wav")
        system_file = self._save_audio(self.system_data, f"system_{timestamp}.wav")
        
        return {
            'mic_file': mic_file,
            'system_file': system_file,
            'duration': len(self.mic_data) / self.settings.audio['sample_rate'] if self.mic_data else 0
        }
    
    def _record_mic(self, device=None):
        """录制麦克风"""
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
    
    def _record_system(self, device=None):
        """录制系统音频"""
        if device is None:
            print("跳过系统音频录制：未找到合适设备")
            return
            
        def callback(indata, frames, time, status):
            if self.is_recording:
                self.system_data.extend(indata[:, 0])
        
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
            print(f"系统音频录音错误: {e}")
    
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