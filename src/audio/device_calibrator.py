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
        # 过滤掉明显不相关的设备
        self.input_devices = self._filter_relevant_devices()
        self.is_testing = False
        self.test_results = {}
        self.sample_rate = 44100
        self.block_size = 1024
        self.debug_mode = debug_mode
        
        if debug_mode:
            print(f"调试模式: 找到 {len(self.input_devices)} 个相关输入设备")
    
    def _filter_relevant_devices(self):
        """过滤出相关的输入设备"""
        relevant_devices = []
        for i, d in enumerate(self.devices):
            if d['max_input_channels'] > 0:
                name = d['name'].lower()
                # 跳过明显不相关的设备
                if any(skip in name for skip in ['hdmi', 'displayport', 'nvidia', 'amd']):
                    continue
                relevant_devices.append((i, d))
        return relevant_devices
        
    def test_microphone_devices(self, duration: float = 5.0, callback=None) -> Dict[int, float]:
        """测试麦克风设备 - 用户说话时检测哪个设备有最强信号"""
        results = {}
        streams = {}
        audio_data = {}
        callback_counter = {}
        
        try:
            # 开始测试
            self.is_testing = True
            
            # 为所有设备同时创建音频流
            active_devices = self.input_devices
            
            for device_id, device_info in active_devices:
                if not self.is_testing:
                    break
                    
                try:
                    audio_data[device_id] = []
                    callback_counter[device_id] = 0
                    
                    def make_callback(dev_id):
                        def audio_callback(indata, frames, time, status):
                            if self.is_testing:
                                try:
                                    rms = np.sqrt(np.mean(indata**2))
                                    audio_data[dev_id].append(rms)
                                    
                                    # 减少UI更新频率：每43次回调更新1次（约每秒1次）
                                    callback_counter[dev_id] += 1
                                    if callback and callback_counter[dev_id] % 43 == 0:
                                        callback(dev_id, rms)
                                except:
                                    pass  # 忽略单个设备的回调错误
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
                    # 单个设备失败不影响其他设备
                    if self.debug_mode:
                        print(f"设备 {device_id} 初始化失败: {e}")
                    audio_data[device_id] = []  # 确保有空数据
                    continue
            
            # 测试时间控制
            sleep_interval = 0.1
            total_slept = 0
            while total_slept < duration and self.is_testing:
                time.sleep(sleep_interval)
                total_slept += sleep_interval
            
            self.is_testing = False
            
        finally:
            # 停止所有流
            for stream in streams.values():
                try:
                    stream.stop()
                    stream.close()
                except:
                    pass
        
        # 计算结果
        for device_id in audio_data:
            if audio_data[device_id]:
                try:
                    max_volume = np.max(audio_data[device_id])
                    results[device_id] = max_volume
                except:
                    results[device_id] = 0.0
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
        callback_counter = {}
        
        try:
            # 开始测试
            self.is_testing = True
            
            # 读取测试音频
            with wave.open(test_audio_file, 'rb') as wf:
                reference_audio = np.frombuffer(wf.readframes(-1), dtype=np.int16).astype(np.float32) / 32767.0
            
            # 为所有设备同时创建音频流
            active_devices = self.input_devices
            
            for device_id, device_info in active_devices:
                if not self.is_testing:
                    break
                    
                try:
                    audio_data[device_id] = []
                    callback_counter[device_id] = 0
                    
                    def make_callback(dev_id):
                        def audio_callback(indata, frames, time, status):
                            if self.is_testing:
                                try:
                                    audio_data[dev_id].extend(indata.flatten())
                                    
                                    # 减少UI更新频率：每43次回调更新1次（约每秒1次）
                                    callback_counter[dev_id] += 1
                                    if callback and callback_counter[dev_id] % 43 == 0:
                                        rms = np.sqrt(np.mean(indata**2))
                                        callback(dev_id, rms)
                                except:
                                    pass  # 忽略单个设备的回调错误
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
                    # 单个设备失败不影响其他设备
                    if self.debug_mode:
                        print(f"设备 {device_id} 初始化失败: {e}")
                    audio_data[device_id] = []  # 确保有空数据
                    continue
            
            # 播放测试音频
            try:
                if not self.is_testing:
                    return {}
                
                # 播放音频并使用超时保护
                sd.play(reference_audio, self.sample_rate)
                
                # 分段等待，避免sd.wait()卡死
                audio_duration = len(reference_audio) / self.sample_rate
                total_waited = 0
                wait_interval = 0.1
                while total_waited < audio_duration + 1.0 and self.is_testing:
                    time.sleep(wait_interval)
                    total_waited += wait_interval
                
                # 额外等待捕获完整
                if self.is_testing:
                    time.sleep(0.5)
                    
            except Exception as e:
                if self.debug_mode:
                    print(f"播放测试音频失败: {e}")
            
            self.is_testing = False
            
        finally:
            # 停止所有流
            for stream in streams.values():
                try:
                    stream.stop()
                    stream.close()
                except:
                    pass
        
        # 分析结果
        for device_id in audio_data:
            if len(audio_data[device_id]) > 0:
                try:
                    captured = np.array(audio_data[device_id])
                    volume = np.sqrt(np.mean(captured**2))
                    
                    if volume > 0.001:
                        # 简化的频率分析
                        fft_length = min(len(captured), 22050)  # 限制FFT长度减少计算
                        fft = np.fft.fft(captured[:fft_length])
                        freqs = np.fft.fftfreq(fft_length, 1/self.sample_rate)
                        
                        target_freq = 1000
                        freq_range = 50
                        mask = (np.abs(freqs - target_freq) < freq_range) | (np.abs(freqs + target_freq) < freq_range)
                        target_energy = np.sum(np.abs(fft[mask])**2)
                        total_energy = np.sum(np.abs(fft)**2)
                        
                        if total_energy > 0:
                            correlation_score = target_energy / total_energy
                            results[device_id] = volume * correlation_score
                        else:
                            results[device_id] = 0.0
                    else:
                        results[device_id] = 0.0
                except:
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
            best_mic = None
            if mic_results:
                max_mic_volume = max(mic_results.values())
                if max_mic_volume > 0.001:  # 只有真正检测到声音才选择
                    best_mic = max(mic_results.items(), key=lambda x: x[1])[0]
            
            best_system = None
            if system_results:
                max_system_score = max(system_results.values())
                if max_system_score > 0.001:  # 只有真正检测到信号才选择
                    best_system = max(system_results.items(), key=lambda x: x[1])[0]
            
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