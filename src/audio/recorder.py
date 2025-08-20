import sounddevice as sd
import numpy as np
import wave
import threading
import time
from datetime import datetime
import os
from .post_processor import AudioPostProcessor

class AudioRecorder:
    def __init__(self, settings):
        self.settings = settings
        self.is_recording = False
        self.mic_data = []
        self.speaker_data = []
        self.start_time = None
        
        # 后处理器
        self.post_processor = AudioPostProcessor(settings)
        self.post_processor.start()
        
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
        
        result = {
            'mic_file': mic_file,
            'speaker_file': speaker_file,
            'duration': len(self.mic_data) / self.settings.audio['sample_rate']
        }
        
        return result
    
    def submit_for_post_processing(self, result, call_info):
        """提交录音结果进行后处理"""
        if result and (result.get('mic_file') or result.get('speaker_file')):
            try:
                self.post_processor.submit_recording(
                    result.get('mic_file'),
                    result.get('speaker_file'),
                    call_info
                )
            except Exception as e:
                print(f"后处理提交失败: {e}")
    
    def stop_post_processor(self):
        """停止后处理器"""
        if hasattr(self, 'post_processor'):
            self.post_processor.stop()
    
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
        self.speaker_callback_count = 0
        self.speaker_data_size = 0
        
        def callback(indata, frames, time, status):
            if self.is_recording:
                self.speaker_callback_count += 1
                audio_chunk = indata[:, 0]
                self.speaker_data.extend(audio_chunk)
                self.speaker_data_size += len(audio_chunk)
                
                # 每100次callback输出一次日志
                if self.speaker_callback_count % 100 == 0:
                    volume = max(abs(audio_chunk)) if len(audio_chunk) > 0 else 0
                    print(f"[DEBUG] 系统音频 callback #{self.speaker_callback_count}, 数据长度: {len(audio_chunk)}, 音量: {volume:.4f}, 总数据: {self.speaker_data_size}")
        
        # 如果没有指定设备，尝试自动查找loopback设备
        if device is None:
            from .device_manager import DeviceManager
            dm = DeviceManager()
            device = dm.get_loopback_device()
            if device is None:
                print("警告: 未找到loopback设备，将使用默认输入设备")
                device = dm.get_default_input()
        
        print(f"[DEBUG] 开始系统音频录制，设备ID: {device}")
        
        try:
            with sd.InputStream(
                device=device,
                channels=1,
                samplerate=self.settings.audio['sample_rate'],
                callback=callback,
                blocksize=self.settings.audio['chunk_size']
            ):
                print(f"[DEBUG] 系统音频流已启动")
                while self.is_recording:
                    time.sleep(0.1)
                print(f"[DEBUG] 系统音频录制结束，总 callback: {self.speaker_callback_count}, 总数据: {self.speaker_data_size}")
        except Exception as e:
            print(f"[ERROR] 扬声器录音错误: {e}")
    
    def _save_audio(self, data, filename):
        """保存音频文件"""
        print(f"[DEBUG] 尝试保存文件: {filename}, 数据长度: {len(data) if data else 0}")
        
        if not data:
            print(f"[ERROR] 数据为空，无法保存文件: {filename}")
            return None
            
        filepath = os.path.join(self.settings.recording['output_dir'], filename)
        
        try:
            with wave.open(filepath, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.settings.audio['sample_rate'])
                
                # 转换为 int16
                audio_data = np.array(data, dtype=np.float32)
                audio_data = (audio_data * 32767).astype(np.int16)
                wf.writeframes(audio_data.tobytes())
            
            file_size = os.path.getsize(filepath)
            print(f"[DEBUG] 文件保存成功: {filepath}, 大小: {file_size} 字节")
            return filepath
            
        except Exception as e:
            print(f"[ERROR] 保存文件失败: {filename}, 错误: {e}")
            return None