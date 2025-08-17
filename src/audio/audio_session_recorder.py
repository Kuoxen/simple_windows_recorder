"""
Windows Audio Session 录音器
使用 Windows Audio Session API 拦截应用音频流
"""

import sounddevice as sd
import numpy as np
import threading
import time
from datetime import datetime
import os
import wave

class AudioSessionRecorder:
    def __init__(self, settings):
        self.settings = settings
        self.is_recording = False
        self.mic_data = []
        self.system_data = []
        self.start_time = None
        
    def get_all_loopback_candidates(self):
        """获取所有可能的回环设备"""
        devices = sd.query_devices()
        candidates = []
        
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                name = device['name'].lower()
                # 扩大搜索范围
                keywords = [
                    'loopback', 'stereo mix', 'what u hear', 'wave out mix',
                    '立体声混音', '混音', 'stereo input',
                    'realtek', 'audio', 'sound'  # 声卡相关
                ]
                
                if any(keyword in name for keyword in keywords):
                    candidates.append((i, device))
        
        return candidates
    
    def start_recording(self, mic_device=None, force_loopback_device=None):
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
        if force_loopback_device is not None:
            system_device = force_loopback_device
        else:
            candidates = self.get_all_loopback_candidates()
            system_device = candidates[0][0] if candidates else None
        
        print(f"麦克风设备: {mic_device if mic_device is not None else '默认'}")
        print(f"系统音频设备: {system_device}")
        
        if system_device is None:
            print("警告: 无法找到系统音频录制设备")
        
        # 启动录音线程
        self.mic_thread = threading.Thread(target=self._record_mic, args=(mic_device,))
        self.system_thread = threading.Thread(target=self._record_system_enhanced, args=(system_device,))
        
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
        mic_file = self._save_audio(self.mic_data, f"mic_session_{timestamp}.wav")
        system_file = self._save_audio(self.system_data, f"system_session_{timestamp}.wav")
        
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
    
    def _record_system_enhanced(self, device=None):
        """增强的系统音频录制"""
        if device is None:
            print("跳过系统音频录制：未找到合适设备")
            return
        
        def callback(indata, frames, time, status):
            if self.is_recording:
                # 增强音频处理
                audio_data = indata[:, 0]
                
                # 检测音频活动
                volume = np.sqrt(np.mean(audio_data**2))
                if volume > 0.001:  # 有音频活动
                    self.system_data.extend(audio_data)
                else:
                    # 静音时也要保持时间同步
                    self.system_data.extend(np.zeros_like(audio_data))
        
        try:
            # 尝试更高的采样率和缓冲区设置
            with sd.InputStream(
                device=device,
                channels=1,
                samplerate=self.settings.audio['sample_rate'],
                callback=callback,
                blocksize=self.settings.audio['chunk_size'],
                latency='low'  # 低延迟模式
            ):
                print(f"开始录制设备 [{device}]...")
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