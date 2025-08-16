import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import Settings
from audio.device_manager import DeviceManager
from audio.recorder import AudioRecorder
import time

def main():
    # 加载配置
    settings = Settings("../config.yaml")
    
    # 初始化设备管理器
    device_manager = DeviceManager()
    print("可用音频设备:")
    device_manager.print_devices()
    
    # 初始化录音器
    recorder = AudioRecorder(settings)
    
    print("\n开始录音测试...")
    print("按 Enter 开始录音，再按 Enter 停止录音")
    
    input("按 Enter 开始录音...")
    
    # 开始录音
    if recorder.start_recording():
        print("录音中... 按 Enter 停止")
        input()
        
        # 停止录音
        result = recorder.stop_recording()
        if result:
            print(f"录音完成!")
            print(f"麦克风文件: {result['mic_file']}")
            print(f"扬声器文件: {result['speaker_file']}")
            print(f"录音时长: {result['duration']:.2f} 秒")
        else:
            print("录音失败")
    else:
        print("无法开始录音")

if __name__ == "__main__":
    main()