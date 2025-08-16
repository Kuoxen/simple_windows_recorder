import sounddevice as sd
import numpy as np
import wave
import threading
import time
from datetime import datetime
import os

class AudioRecorder:
    def __init__(self, settings):
        self.settings = settings
        self.is_recording = False
        self.mic_data = []
        self.speaker_data = []
        self.start_time = None
        
    def start_recording(self, mic_device=None, speaker_device=None):
        """开始录音"""
        if self.is_recording:
            return False
            
        self.is_recording = True
        self.mic_data = []
        self.speaker_data = []
        self.start_time = datetime.now()
        
        # 创建输出目录
        os.makedirs(self.settings.recording['output_dir'], exist_ok=True)
        
        # 打印使用的设备信息
        print(f"麦克风设备: {mic_device if mic_device is not None else '默认'}")
        print(f"扬声器设备: {speaker_device if speaker_device is not None else '自动检测'}")
        
        # 启动两个录音线程
        self.mic_thread = threading.Thread(target=self._record_mic, args=(mic_device,))
        self.speaker_thread = threading.Thread(target=self._record_speaker, args=(speaker_device,))
        
        self.mic_thread.start()
        self.speaker_thread.start()
        
        return True
    
    def stop_recording(self):
        """停止录音"""
        if not self.is_recording:
            return None
            
        self.is_recording = False
        
        # 等待线程结束
        self.mic_thread.join()
        self.speaker_thread.join()
        
        # 保存文件
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        mic_file = self._save_audio(self.mic_data, f"mic_{timestamp}.wav")
        speaker_file = self._save_audio(self.speaker_data, f"speaker_{timestamp}.wav")
        
        return {
            'mic_file': mic_file,
            'speaker_file': speaker_file,
            'duration': len(self.mic_data) / self.settings.audio['sample_rate']
        }
    
    def _record_mic(self, device=None):
        """录制麦克风"""
        def callback(indata, frames, time, status):
            if self.is_recording:
                self.mic_data.extend(indata[:, 0])
        
        with sd.InputStream(
            device=device,
            channels=1,
            samplerate=self.settings.audio['sample_rate'],
            callback=callback,
            blocksize=self.settings.audio['chunk_size']
        ):
            while self.is_recording:
                time.sleep(0.1)
    
    def _record_speaker(self, device=None):
        """录制扬声器回环"""
        def callback(indata, frames, time, status):
            if self.is_recording:
                self.speaker_data.extend(indata[:, 0])
        
        # 如果没有指定设备，尝试自动查找loopback设备
        if device is None:
            from .device_manager import DeviceManager
            dm = DeviceManager()
            device = dm.get_loopback_device()
            if device is None:
                print("警告: 未找到loopback设备，将使用默认输入设备")
                device = dm.get_default_input()
        
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
            print(f"扬声器录音错误: {e}")
    
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