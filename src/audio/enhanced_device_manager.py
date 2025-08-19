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
        try:
            import time
            test_success = False
            
            def test_callback(indata, frames, time, status):
                nonlocal test_success
                test_success = True
            
            # 使用与实际录音相同的回调模式
            with sd.InputStream(
                device=device_id, 
                channels=1, 
                samplerate=44100, 
                callback=test_callback,
                blocksize=1024
            ):
                time.sleep(0.1)  # 短暂测试
            
            return True  # 只要能打开就认为可用
            
        except Exception as e:
            # 过滤掉WDM-KS相关的错误，这些设备在回调模式下可能可用
            error_msg = str(e).lower()
            if 'wdm-ks' in error_msg or 'blocking api not supported' in error_msg:
                self.logger.info(f"设备 {device_id} 使用WDM-KS驱动，跳过检测")
                return True  # WDM-KS设备在回调模式下通常可用
            
            self.logger.warning(f"设备 {device_id} 不可用: {e}")
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
            print(f"  {status} [{i}] {device['name']} - {device['max_input_channels']}ch")
        
        # 输出设备
        print("\n📤 输出设备:")
        output_devices = self.get_output_devices()
        for i, device in output_devices:
            print(f"  [{i}] {device['name']} - {device['max_output_channels']}ch")
        
        # 回环设备
        print("\n🔄 检测到的回环设备:")
        loopback_devices = self.get_loopback_devices()
        if loopback_devices:
            for device_id, device in loopback_devices:
                status = "✅" if self.test_device_availability(device_id) else "❌"
                print(f"  {status} [{device_id}] {device['name']}")
            
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
                print(f"  {status} [{device_id}] {device['name']}")
        else:
            print("  ⚠️  未找到物理麦克风设备")
    
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