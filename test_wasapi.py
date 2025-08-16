#!/usr/bin/env python3
"""
WASAPI 录音测试
测试是否能录制蓝牙耳机等任意输出设备的音频
"""

import sys
import os
sys.path.append('src')

from src.config.settings import Settings
from src.audio.device_manager import DeviceManager
from src.audio.wasapi_recorder import WASAPIRecorder

def main():
    print("=== WASAPI 录音测试 ===")
    
    settings = Settings("config.yaml")
    device_manager = DeviceManager()
    
    # 显示当前默认设备
    default_input = device_manager.get_default_input()
    default_output = device_manager.get_default_output()
    
    print(f"当前默认输入设备: [{default_input}] {device_manager.devices[default_input]['name']}")
    print(f"当前默认输出设备: [{default_output}] {device_manager.devices[default_output]['name']}")
    
    # 使用WASAPI录音器
    recorder = WASAPIRecorder(settings)
    
    print(f"\n=== 测试说明 ===")
    print("这个测试会尝试录制当前默认输出设备的音频")
    print("无论是扬声器、蓝牙耳机还是USB耳机都应该能录制到")
    print("请确保你的音频正在通过默认输出设备播放")
    
    input("\n按回车开始录音...")
    
    if recorder.start_recording():
        print("\n🎙️  录音中...")
        print("💡 现在请:")
        print("   1. 对着麦克风说话")
        print("   2. 播放一些音频（音乐、视频等）")
        print("   3. 确保音频通过你当前的输出设备播放")
        
        input("\n测试完成后按回车停止录音...")
        
        result = recorder.stop_recording()
        if result:
            print(f"\n✅ 录音完成!")
            print(f"📁 麦克风文件: {result['mic_file']}")
            print(f"📁 系统音频文件: {result['system_file']}")
            print(f"⏱️  录音时长: {result['duration']:.2f} 秒")
            
            # 检查文件
            if result['system_file'] and os.path.exists(result['system_file']):
                size = os.path.getsize(result['system_file'])
                print(f"📊 系统音频文件大小: {size} 字节")
                if size < 1000:
                    print("⚠️  系统音频文件很小，可能没有录到声音")
                    print("💡 请检查:")
                    print("   - 是否有音频在播放")
                    print("   - 音频是否通过默认输出设备播放")
                else:
                    print("✅ 系统音频文件大小正常")
            else:
                print("❌ 系统音频录制失败")
        else:
            print("❌ 录音失败")
    else:
        print("❌ 无法开始录音")

if __name__ == "__main__":
    main()