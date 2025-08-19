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
        
        # 输入设备
        print("\n📥 输入设备:")
        input_devices = self.get_input_devices()
        for i, device in input_devices:
            status = "✅" if self.test_device_availability(i) else "❌"
            # 显示更多信息：通道数、默认采样率、主机 API
            channels = device['max_input_channels']
            samplerate = int(device.get('default_samplerate', 0))
            hostapi = device.get('hostapi', -1)
            hostapi_name = self._get_hostapi_name(hostapi)
            
            print(f"  {status} [{i:2d}] {device['name'][:50]:<50} | {channels}ch | {samplerate:>5}Hz | {hostapi_name}")
        
        # 输出设备
        print("\n📤 输出设备:")
        output_devices = self.get_output_devices()
        for i, device in output_devices:
            channels = device['max_output_channels']
            samplerate = int(device.get('default_samplerate', 0))
            hostapi = device.get('hostapi', -1)
            hostapi_name = self._get_hostapi_name(hostapi)
            
            print(f"  [{i:2d}] {device['name'][:50]:<50} | {channels}ch | {samplerate:>5}Hz | {hostapi_name}")
        
        # 回环设备
        print("\n🔄 检测到的回环设备:")
        loopback_devices = self.get_loopback_devices()
        if loopback_devices:
            for device_id, device in loopback_devices:
                status = "✅" if self.test_device_availability(device_id) else "❌"
                channels = device['max_input_channels']
                samplerate = int(device.get('default_samplerate', 0))
                hostapi = device.get('hostapi', -1)
                hostapi_name = self._get_hostapi_name(hostapi)
                
                print(f"  {status} [{device_id:2d}] {device['name'][:45]:<45} | {channels}ch | {samplerate:>5}Hz | {hostapi_name}")
            
            best_loopback = self.get_best_loopback_device()
            if best_loopback is not None:
                print(f"  🎯 推荐使用: [{best_loopback}] {self.devices[best_loopback]['name']}")
        else:
            print("  ⚠️  未找到回环设备")
            print("  💡 建议安装 VB-Cable 或启用立体声混音")
        
        # 物理麦克风
        print("\n🎤 物理麦克风设备:")
        physical_mics = self.get_physical_microphones()
        if physical_mics:
            for device_id, device in physical_mics:
                status = "✅" if self.test_device_availability(device_id) else "❌"
                channels = device['max_input_channels']
                samplerate = int(device.get('default_samplerate', 0))
                hostapi = device.get('hostapi', -1)
                hostapi_name = self._get_hostapi_name(hostapi)
                
                print(f"  {status} [{device_id:2d}] {device['name'][:45]:<45} | {channels}ch | {samplerate:>5}Hz | {hostapi_name}")
        else:
            print("  ⚠️  未找到物理麦克风设备")
            
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
        """获取推荐的设备配置"""
        recommendations = {
            'microphone': None,
            'system_audio': None
        }
        
        # 推荐麦克风
        physical_mics = self.get_physical_microphones()
        if physical_mics:
            # 选择第一个可用的物理麦克风
            for device_id, device in physical_mics:
                if self.test_device_availability(device_id):
                    recommendations['microphone'] = device_id
                    break
        
        # 推荐系统音频设备
        best_loopback = self.get_best_loopback_device()
        if best_loopback is not None and self.test_device_availability(best_loopback):
            recommendations['system_audio'] = best_loopback
        
        return recommendations
    
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