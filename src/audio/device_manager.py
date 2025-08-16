import sounddevice as sd
import platform

class DeviceManager:
    def __init__(self):
        self.devices = sd.query_devices()
        self.system = platform.system()
    
    def get_input_devices(self):
        """获取输入设备（麦克风）"""
        return [(i, d) for i, d in enumerate(self.devices) if d['max_input_channels'] > 0]
    
    def get_output_devices(self):
        """获取输出设备（扬声器）"""
        return [(i, d) for i, d in enumerate(self.devices) if d['max_output_channels'] > 0]
    
    def get_loopback_device(self):
        """获取回环设备（用于录制系统音频）"""
        if self.system == "Windows":
            for i, device in enumerate(self.devices):
                name = device['name'].lower()
                # Windows回环设备关键词
                windows_keywords = [
                    'loopback', 'stereo mix', 'what u hear', 'wave out mix',
                    '立体声混音', '混音', 'stereo input'
                ]
                if any(keyword in name for keyword in windows_keywords):
                    return i
        elif self.system == "Darwin":
            for i, device in enumerate(self.devices):
                name = device['name'].lower()
                if any(keyword in name for keyword in ['blackhole', 'soundflower', 'virtual']):
                    return i
        return None
    
    def get_default_input(self):
        """获取默认输入设备"""
        return sd.default.device[0]
    
    def get_default_output(self):
        """获取默认输出设备"""
        return sd.default.device[1]
    
    def print_devices(self):
        """打印所有设备信息"""
        print("=== 音频设备列表 ===")
        for i, device in enumerate(self.devices):
            device_type = []
            if device['max_input_channels'] > 0:
                device_type.append("输入")
            if device['max_output_channels'] > 0:
                device_type.append("输出")
            print(f"[{i}] {device['name']} - {'/'.join(device_type)}")
            
        loopback = self.get_loopback_device()
        if loopback:
            print(f"\n找到回环设备: [{loopback}] {self.devices[loopback]['name']}")
        else:
            print(f"\n未找到回环设备 (系统: {self.system})")
            if self.system == "Darwin":
                print("提示: macOS 需要安装 BlackHole 等虚拟音频设备")