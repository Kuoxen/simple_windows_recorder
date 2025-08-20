import sounddevice as sd
import numpy as np
import threading
import time
from typing import Dict, List, Tuple, Optional
import wave
import tempfile
import os

class DeviceCalibrator:
    """设备校准器 - 通过实际音频测试自动选择最佳设备"""
    
    def __init__(self, debug_mode=False):
        self.devices = sd.query_devices()
        self.input_devices = [(i, d) for i, d in enumerate(self.devices) if d['max_input_channels'] > 0]
        self.is_testing = False
        self.test_results = {}
        self.sample_rate = 44100
        self.block_size = 1024
        self.debug_mode = debug_mode
        
        if debug_mode:
            print(f"调试模式: 找到 {len(self.input_devices)} 个输入设备")
        
    def test_microphone_devices(self, duration: float = 5.0, callback=None) -> Dict[int, float]:
        """测试麦克风设备 - 用户说话时检测哪个设备有最强信号"""
        results = {}
        streams = {}
        audio_data = {}
        
        # 为每个输入设备创建音频流
        for device_id, device_info in self.input_devices:
            try:
                audio_data[device_id] = []
                
                def make_callback(dev_id):
                    def audio_callback(indata, frames, time, status):
                        if self.is_testing:
                            # 计算RMS音量
                            rms = np.sqrt(np.mean(indata**2))
                            audio_data[dev_id].append(rms)
                            
                            # 实时回调更新UI
                            if callback:
                                callback(dev_id, rms)
                    return audio_callback
                
                stream = sd.InputStream(
                    device=device_id,
                    channels=1,
                    samplerate=self.sample_rate,
                    blocksize=self.block_size,
                    callback=make_callback(device_id)
                )
                streams[device_id] = stream
                stream.start()
                
            except Exception as e:
                print(f"无法打开设备 {device_id}: {e}")
                continue
        
        # 开始测试
        self.is_testing = True
        if self.debug_mode:
            print(f"开始麦克风测试，时长: {duration}秒")
        time.sleep(duration)
        self.is_testing = False
        
        if self.debug_mode:
            print("麦克风测试完成")
        
        # 停止所有流
        for stream in streams.values():
            stream.stop()
            stream.close()
        
        # 计算每个设备的平均音量
        for device_id in audio_data:
            if audio_data[device_id]:
                avg_volume = np.mean(audio_data[device_id])
                max_volume = np.max(audio_data[device_id])
                results[device_id] = max_volume  # 使用峰值作为判断标准
            else:
                results[device_id] = 0.0
        
        return results
    
    def generate_test_audio(self, duration: float = 3.0) -> str:
        """生成测试音频文件"""
        # 生成1kHz正弦波
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        frequency = 1000  # 1kHz
        audio = 0.3 * np.sin(2 * np.pi * frequency * t)  # 30%音量
        
        # 保存到临时文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        with wave.open(temp_file.name, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes((audio * 32767).astype(np.int16).tobytes())
        
        return temp_file.name
    
    def test_system_audio_devices(self, test_audio_file: str, callback=None) -> Dict[int, float]:
        """测试系统音频设备 - 播放音频时检测哪个设备能捕获到"""
        results = {}
        streams = {}
        audio_data = {}
        
        # 读取测试音频作为参考
        with wave.open(test_audio_file, 'rb') as wf:
            reference_audio = np.frombuffer(wf.readframes(-1), dtype=np.int16).astype(np.float32) / 32767.0
        
        # 为每个输入设备创建音频流
        for device_id, device_info in self.input_devices:
            try:
                audio_data[device_id] = []
                
                def make_callback(dev_id):
                    def audio_callback(indata, frames, time, status):
                        if self.is_testing:
                            # 记录音频数据
                            audio_data[dev_id].extend(indata.flatten())
                            
                            # 计算当前音量用于UI显示
                            rms = np.sqrt(np.mean(indata**2))
                            if callback:
                                callback(dev_id, rms)
                    return audio_callback
                
                stream = sd.InputStream(
                    device=device_id,
                    channels=1,
                    samplerate=self.sample_rate,
                    blocksize=self.block_size,
                    callback=make_callback(device_id)
                )
                streams[device_id] = stream
                stream.start()
                
            except Exception as e:
                print(f"无法打开设备 {device_id}: {e}")
                continue
        
        # 开始测试
        self.is_testing = True
        
        # 播放测试音频
        try:
            if self.debug_mode:
                print("开始播放测试音频...")
            sd.play(reference_audio, self.sample_rate)
            sd.wait()  # 等待播放完成
            time.sleep(0.5)  # 额外等待确保捕获完整
            if self.debug_mode:
                print("测试音频播放完成")
        except Exception as e:
            print(f"播放测试音频失败: {e}")
            if self.debug_mode:
                print("注意: 在Mac上可能无法正确测试系统音频捕获")
        
        self.is_testing = False
        
        # 停止所有流
        for stream in streams.values():
            stream.stop()
            stream.close()
        
        # 分析每个设备捕获的音频与参考音频的相关性
        for device_id in audio_data:
            if len(audio_data[device_id]) > 0:
                captured = np.array(audio_data[device_id])
                
                # 计算音量作为基础指标
                volume = np.sqrt(np.mean(captured**2))
                
                # 如果音量足够大，进行相关性分析
                if volume > 0.001:  # 音量阈值
                    # 简化的相关性检测：检查是否有明显的1kHz频率成分
                    fft = np.fft.fft(captured)
                    freqs = np.fft.fftfreq(len(captured), 1/self.sample_rate)
                    
                    # 找到1kHz附近的能量
                    target_freq = 1000
                    freq_range = 50  # ±50Hz
                    mask = (np.abs(freqs - target_freq) < freq_range) | (np.abs(freqs + target_freq) < freq_range)
                    target_energy = np.sum(np.abs(fft[mask])**2)
                    total_energy = np.sum(np.abs(fft)**2)
                    
                    if total_energy > 0:
                        correlation_score = target_energy / total_energy
                        results[device_id] = volume * correlation_score  # 综合评分
                    else:
                        results[device_id] = 0.0
                else:
                    results[device_id] = 0.0
            else:
                results[device_id] = 0.0
        
        return results
    
    def calibrate_devices(self, mic_test_duration: float = 5.0, 
                         system_test_duration: float = 3.0,
                         progress_callback=None) -> Tuple[Optional[int], Optional[int]]:
        """完整的设备校准流程"""
        
        if progress_callback:
            progress_callback("开始麦克风测试...", 0)
        
        # 1. 测试麦克风设备
        mic_results = self.test_microphone_devices(mic_test_duration)
        
        if progress_callback:
            progress_callback("麦克风测试完成，开始系统音频测试...", 50)
        
        # 2. 生成测试音频
        test_audio_file = self.generate_test_audio(system_test_duration)
        
        try:
            # 3. 测试系统音频设备
            system_results = self.test_system_audio_devices(test_audio_file)
            
            if progress_callback:
                progress_callback("设备校准完成", 100)
            
            # 4. 选择最佳设备
            best_mic = max(mic_results.items(), key=lambda x: x[1])[0] if mic_results else None
            best_system = max(system_results.items(), key=lambda x: x[1])[0] if system_results else None
            
            # 存储测试结果
            self.test_results = {
                'microphone': mic_results,
                'system_audio': system_results,
                'selected_mic': best_mic,
                'selected_system': best_system
            }
            
            return best_mic, best_system
            
        finally:
            # 清理临时文件
            try:
                os.unlink(test_audio_file)
            except:
                pass
    
    def get_device_name(self, device_id: int) -> str:
        """获取设备名称"""
        if 0 <= device_id < len(self.devices):
            return self.devices[device_id]['name']
        return f"设备 {device_id}"
    
    def get_test_results(self) -> Dict:
        """获取测试结果"""
        return self.test_results