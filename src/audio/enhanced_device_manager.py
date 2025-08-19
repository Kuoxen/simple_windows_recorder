import sounddevice as sd
import platform
import logging
from typing import List, Tuple, Optional, Dict

class EnhancedDeviceManager:
    """增强版设备管理器，提供更健壮的音频设备检测和管理"""
    
    def __init__(self):
        self.devices = sd.query_devices()
        self.system = platform.system()
        self.logger = logging.getLogger(__name__)
        
    def _get_hostapi_name(self, hostapi_id: int) -> str:
        """安全获取主机API名称"""
        try:
            if hostapi_id >= 0:
                return sd.query_hostapis()[hostapi_id]['name']
            return 'Unknown'
        except:
            return f'API-{hostapi_id}'
        
    def get_input_devices(self) -> List[Tuple[int, Dict]]:
        """获取输入设备（麦克风）"""
        return [(i, d) for i, d in enumerate(self.devices) if d['max_input_channels'] > 0]
    
    def get_output_devices(self) -> List[Tuple[int, Dict]]:
        """获取输出设备（扬声器）"""
        return [(i, d) for i, d in enumerate(self.devices) if d['max_output_channels'] > 0]
    
    def get_loopback_devices(self) -> List[Tuple[int, Dict]]:
        """获取所有可能的回环设备"""
        loopback_devices = []
        
        if self.system == "Windows":
            # Windows 回环设备关键词（更全面）
            windows_keywords = [
                'loopback', 'stereo mix', 'what u hear', 'wave out mix',
                '立体声混音', '混音', 'stereo input', 'cable output',
                'vb-cable', 'virtual cable', 'voicemeeter', 'blackhole'
            ]
            
            for i, device in enumerate(self.devices):
                if device['max_input_channels'] > 0:
                    name = device['name'].lower()
                    if any(keyword in name for keyword in windows_keywords):
                        loopback_devices.append((i, device))
                        
        elif self.system == "Darwin":  # macOS
            mac_keywords = ['blackhole', 'soundflower', 'virtual', 'loopback']
            for i, device in enumerate(self.devices):
                if device['max_input_channels'] > 0:
                    name = device['name'].lower()
                    if any(keyword in name for keyword in mac_keywords):
                        loopback_devices.append((i, device))
        
        return loopback_devices
    
    def get_best_loopback_device(self) -> Optional[int]:
        """获取最佳的回环设备"""
        loopback_devices = self.get_loopback_devices()
        
        if not loopback_devices:
            return None
            
        # 优先级排序
        priority_keywords = [
            'cable output',  # VB-Cable Output (最常用)
            'stereo mix',    # Windows 立体声混音
            '立体声混音',     # 中文立体声混音
            'blackhole',     # macOS BlackHole
            'voicemeeter',   # Voicemeeter
            'loopback'       # 通用 loopback
        ]
        
        for keyword in priority_keywords:
            for device_id, device in loopback_devices:
                if keyword in device['name'].lower():
                    return device_id
        
        # 如果没有匹配优先级，返回第一个
        return loopback_devices[0][0]
    
    def get_physical_microphones(self) -> List[Tuple[int, Dict]]:
        """获取物理麦克风设备（排除虚拟设备）"""
        input_devices = self.get_input_devices()
        physical_mics = []
        
        # 排除的虚拟设备关键词
        virtual_keywords = [
            'cable output', 'cable input', 'stereo mix', '立体声混音',
            'blackhole', 'soundflower', 'voicemeeter', 'virtual',
            'loopback', 'what u hear', 'wave out mix'
        ]
        
        for device_id, device in input_devices:
            name = device['name'].lower()
            is_virtual = any(keyword in name for keyword in virtual_keywords)
            if not is_virtual:
                physical_mics.append((device_id, device))
        
        return physical_mics
    
    def test_device_availability(self, device_id: int) -> bool:
        """测试设备是否可用（使用回调模式）"""
        import time
        
        # 尝试多种采样率
        sample_rates = [44100, 48000, 22050, 16000, 8000]
        
        for samplerate in sample_rates:
            try:
                def test_callback(indata, frames, time, status):
                    pass
                
                # 使用与实际录音相同的回调模式
                with sd.InputStream(
                    device=device_id, 
                    channels=1, 
                    samplerate=samplerate, 
                    callback=test_callback,
                    blocksize=1024
                ):
                    time.sleep(0.05)  # 更短的测试时间
                
                return True  # 成功打开
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # 过滤掉一些可以忽略的错误
                if any(keyword in error_msg for keyword in [
                    'wdm-ks', 'blocking api not supported', 
                    'invalid sample rate'  # 采样率错误继续尝试
                ]):
                    continue  # 尝试下一个采样率
                
                # 其他错误认为设备不可用
                if 'invalid device' in error_msg:
                    self.logger.warning(f"设备 {device_id} 无效: {e}")
                    return False
                    
                # 继续尝试其他采样率
                continue
        
        # 所有采样率都失败
        self.logger.warning(f"设备 {device_id} 不支持任何测试采样率")
        return False
    
    def get_device_info(self, device_id: int) -> Optional[Dict]:
        """获取设备详细信息"""
        try:
            if 0 <= device_id < len(self.devices):
                return self.devices[device_id]
        except:
            pass
        return None
    
    def print_devices(self):
        """打印所有设备信息（增强版）"""
        print("=== 音频设备列表 ===")
        
        # 显示系统默认设备
        default_input = self.get_default_input()
        default_output = self.get_default_output()
        print(f"\n🎯 系统默认设备:")
        if default_input is not None:
            input_name = self.devices[default_input]['name'] if default_input < len(self.devices) else 'Unknown'
            print(f"  输入: [{default_input}] {input_name}")
        else:
            print(f"  输入: 未设置")
            
        if default_output is not None:
            output_name = self.devices[default_output]['name'] if default_output < len(self.devices) else 'Unknown'
            print(f"  输出: [{default_output}] {output_name}")
        else:
            print(f"  输出: 未设置")
        
        # 所有输入设备（参考）
        print("\n📥 所有输入设备（参考）:")
        input_devices = self.get_input_devices()
        for i, device in input_devices:
            status = "✅" if self.test_device_availability(i) else "❌"
            channels = device['max_input_channels']
            samplerate = int(device.get('default_samplerate', 0))
            hostapi = device.get('hostapi', -1)
            hostapi_name = self._get_hostapi_name(hostapi)
            
            # 标记特殊设备
            tags = []
            if i == default_input:
                tags.append("默认")
            if self._can_capture_system_input(i, default_input or -1):
                tags.append("可录麦克风")
            if self._can_capture_system_output(i, default_output or -1):
                tags.append("可录系统")
            
            tag_str = f" [{','.join(tags)}]" if tags else ""
            print(f"  {status} [{i:2d}] {device['name'][:40]:<40}{tag_str} | {channels}ch | {samplerate:>5}Hz | {hostapi_name}")
        
        # 所有输出设备（参考）
        print("\n📤 所有输出设备（参考）:")
        output_devices = self.get_output_devices()
        for i, device in output_devices:
            channels = device['max_output_channels']
            samplerate = int(device.get('default_samplerate', 0))
            hostapi = device.get('hostapi', -1)
            hostapi_name = self._get_hostapi_name(hostapi)
            
            is_default = " [默认]" if i == default_output else ""
            print(f"  [{i:2d}] {device['name'][:40]:<40}{is_default} | {channels}ch | {samplerate:>5}Hz | {hostapi_name}")
        
        # 系统音频设备（能录制系统输出的设备）
        print("\n🔄 系统音频设备（能录制系统输出）:")
        if default_output is not None:
            system_audio_candidates = []
            for device_id, device in self.get_input_devices():
                if self.test_device_availability(device_id) and self._can_capture_system_output(device_id, default_output):
                    system_audio_candidates.append((device_id, device))
            
            if system_audio_candidates:
                for device_id, device in system_audio_candidates:
                    channels = device['max_input_channels']
                    samplerate = int(device.get('default_samplerate', 0))
                    hostapi = device.get('hostapi', -1)
                    hostapi_name = self._get_hostapi_name(hostapi)
                    
                    print(f"  ✅ [{device_id:2d}] {device['name'][:45]:<45} | {channels}ch | {samplerate:>5}Hz | {hostapi_name}")
                
                best_system = self._get_best_system_audio()
                if best_system is not None:
                    print(f"  🎯 推荐使用: [{best_system}] {self.devices[best_system]['name']}")
            else:
                print("  ⚠️  未找到能录制系统输出的设备")
                print("  💡 建议安装 VB-Cable 或启用立体声混音")
        else:
            print("  ⚠️  系统未设置默认输出设备")
        
        # 麦克风设备（能录制系统输入的设备）
        print("\n🎤 麦克风设备（能录制系统输入）:")
        if default_input is not None:
            mic_candidates = []
            for device_id, device in self.get_input_devices():
                if self.test_device_availability(device_id) and self._can_capture_system_input(device_id, default_input):
                    mic_candidates.append((device_id, device))
            
            if mic_candidates:
                for device_id, device in mic_candidates:
                    channels = device['max_input_channels']
                    samplerate = int(device.get('default_samplerate', 0))
                    hostapi = device.get('hostapi', -1)
                    hostapi_name = self._get_hostapi_name(hostapi)
                    
                    # 标记是否是默认设备
                    is_default = " [默认]" if device_id == default_input else ""
                    print(f"  ✅ [{device_id:2d}] {device['name'][:40]:<40}{is_default} | {channels}ch | {samplerate:>5}Hz | {hostapi_name}")
                
                best_mic = self._get_best_microphone()
                if best_mic is not None:
                    print(f"  🎯 推荐使用: [{best_mic}] {self.devices[best_mic]['name']}")
            else:
                print("  ⚠️  未找到能录制系统输入的设备")
        else:
            print("  ⚠️  系统未设置默认输入设备")
        
        # 显示主机 API 信息
        print("\n🔌 主机 API 信息:")
        try:
            hostapis = sd.query_hostapis()
            for i, api in enumerate(hostapis):
                default_input = api.get('default_input_device', -1)
                default_output = api.get('default_output_device', -1)
                device_count = api.get('device_count', len([d for d in self.devices if d.get('hostapi') == i]))
                print(f"  [{i}] {api.get('name', 'Unknown')} - 输入:{default_input} 输出:{default_output} 设备数:{device_count}")
        except Exception as e:
            print(f"  ⚠️  获取主机 API 信息失败: {e}")
        
        # 显示推荐结果总结
        print("\n🎆 智能推荐结果:")
        recommendations = self.get_recommended_devices()
        if recommendations['microphone'] is not None:
            mic_name = self.devices[recommendations['microphone']]['name']
            print(f"  🎤 麦克风: [{recommendations['microphone']}] {mic_name}")
        else:
            print(f"  🎤 麦克风: 无可用设备")
            
        if recommendations['system_audio'] is not None:
            sys_name = self.devices[recommendations['system_audio']]['name']
            print(f"  🔊 系统音频: [{recommendations['system_audio']}] {sys_name}")
        else:
            print(f"  🔊 系统音频: 无可用设备")
    
    def get_default_input(self) -> Optional[int]:
        """获取默认输入设备"""
        try:
            return sd.default.device[0]
        except:
            return None
    
    def get_default_output(self) -> Optional[int]:
        """获取默认输出设备"""
        try:
            return sd.default.device[1]
        except:
            return None
    
    def get_recommended_devices(self) -> Dict[str, Optional[int]]:
        """获取推荐的设备配置（动态推荐）"""
        recommendations = {
            'microphone': None,
            'system_audio': None
        }
        
        # 动态推荐麦克风
        recommendations['microphone'] = self._get_best_microphone()
        
        # 动态推荐系统音频
        recommendations['system_audio'] = self._get_best_system_audio()
        
        return recommendations
    
    def _get_best_microphone(self) -> Optional[int]:
        """找到能录制系统当前麦克风输入的最佳设备"""
        default_input = self.get_default_input()
        if default_input is None:
            return None
        
        # 找到所有能录制系统默认麦克风的设备
        input_devices = self.get_input_devices()
        candidates = []
        
        for device_id, device in input_devices:
            if not self.test_device_availability(device_id):
                continue
                
            # 测试是否能录制到系统麦克风输入
            if self._can_capture_system_input(device_id, default_input):
                candidates.append((device_id, device))
        
        if not candidates:
            return None
        
        # 从候选者中选择最佳设备
        return self._select_best_input_device(candidates)
    
    def _can_capture_system_input(self, device_id: int, default_input: int) -> bool:
        """测试设备是否能录制到系统麦克风输入"""
        # 直接是默认设备
        if device_id == default_input:
            return True
            
        device = self.get_device_info(device_id)
        if not device:
            return False
            
        name = device['name'].lower()
        
        # 声音映射器通常指向默认设备
        if 'microsoft' in name and 'mapper' in name:
            return True
            
        # 通信设备映射器
        if 'communication' in name and 'mapper' in name:
            return True
            
        # 其他情况需要实际测试（这里简化处理）
        return False
    
    def _select_best_input_device(self, candidates) -> int:
        """从候选设备中选择最佳的"""
        if len(candidates) == 1:
            return candidates[0][0]
            
        # 多个候选者时，优先选择非映射器设备（直接设备通常质量更好）
        for device_id, device in candidates:
            name = device['name'].lower()
            if 'mapper' not in name:
                return device_id
                
        # 都是映射器时，选择第一个
        return candidates[0][0]
    
    def _get_best_system_audio(self) -> Optional[int]:
        """找到能录制系统当前音频输出的最佳设备"""
        default_output = self.get_default_output()
        if default_output is None:
            return None
        
        # 找到所有能录制系统默认输出的设备
        input_devices = self.get_input_devices()
        candidates = []
        
        for device_id, device in input_devices:
            if not self.test_device_availability(device_id):
                continue
                
            # 测试是否能录制到系统音频输出
            if self._can_capture_system_output(device_id, default_output):
                candidates.append((device_id, device))
        
        if not candidates:
            return None
        
        # 从候选者中选择最佳设备
        return self._select_best_loopback_device(candidates)
    
    def _can_capture_system_output(self, device_id: int, default_output: int) -> bool:
        """测试设备是否能录制到系统音频输出"""
        device = self.get_device_info(device_id)
        if not device:
            return False
            
        name = device['name'].lower()
        
        # 检查是否是已知的loopback设备
        loopback_keywords = [
            'cable output', 'stereo mix', '立体声混音', 'what u hear', 
            'wave out mix', 'blackhole', 'soundflower', 'voicemeeter', 'loopback'
        ]
        
        return any(keyword in name for keyword in loopback_keywords)
    
    def _select_best_loopback_device(self, candidates) -> int:
        """从候选loopback设备中选择最佳的"""
        if len(candidates) == 1:
            return candidates[0][0]
            
        # 多个候选者时，按质量优先级选择
        priority_order = [
            'cable output',    # VB-Cable最优
            'blackhole',       # macOS BlackHole
            'stereo mix',      # Windows立体声混音
            '立体声混音',     # 中文立体声混音
            'voicemeeter',     # Voicemeeter
            'loopback'         # 通用loopback
        ]
        
        for keyword in priority_order:
            for device_id, device in candidates:
                if keyword in device['name'].lower():
                    return device_id
                    
        # 都不匹配时，选择第一个
        return candidates[0][0]
    
    def get_device_details(self, device_id: int) -> str:
        """获取设备详细信息字符串"""
        device = self.get_device_info(device_id)
        if not device:
            return "Unknown Device"
            
        channels = device.get('max_input_channels', 0)
        samplerate = int(device.get('default_samplerate', 0))
        hostapi = device.get('hostapi', -1)
        hostapi_name = self._get_hostapi_name(hostapi)
        
        return f"{device['name']} | {channels}ch | {samplerate}Hz | {hostapi_name}"