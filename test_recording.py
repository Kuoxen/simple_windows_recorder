#!/usr/bin/env python3
"""
录音测试脚本
用于测试麦克风和系统声音采集功能
"""

import sys
import os
sys.path.append('src')

from src.config.settings import Settings
from src.audio.device_manager import DeviceManager
from src.audio.recorder import AudioRecorder

def main():
    print("=== 呼叫中心录音测试 ===")
    
    # 加载配置
    settings = Settings("config.yaml")
    
    # 设备管理
    device_manager = DeviceManager()
    device_manager.print_devices()
    
    # 让用户选择设备
    input_devices = device_manager.get_input_devices()
    
    print(f"\n请选择麦克风设备 (默认: {device_manager.get_default_input()}):")
    for i, (idx, device) in enumerate(input_devices):
        print(f"  {i}: [{idx}] {device['name']}")
    
    mic_choice = input("输入序号 (回车使用默认): ").strip()
    mic_device = None
    if mic_choice.isdigit():
        mic_device = input_devices[int(mic_choice)][0]
    
    # 系统声音设备
    loopback_device = device_manager.get_loopback_device()
    if loopback_device:
        print(f"\n系统声音设备: [{loopback_device}] {device_manager.devices[loopback_device]['name']}")
    else:
        print("\n警告: 未找到系统声音回环设备!")
        print("请确保启用了'立体声混音'或安装了虚拟音频设备")
    
    # 开始测试
    recorder = AudioRecorder(settings)
    
    print("\n=== 测试说明 ===")
    print("1. 打开会议软件(腾讯会议/钉钉等)")
    print("2. 用另一个设备加入会议")
    print("3. 按回车开始录音")
    print("4. 测试对话后按回车停止")
    
    input("\n准备好后按回车开始录音...")
    
    if recorder.start_recording(mic_device, loopback_device):
        print("\n🎙️  录音中...")
        print("💡 现在可以:")
        print("   - 对着麦克风说话 (测试坐席声音)")
        print("   - 让对方说话 (测试客户声音)")
        print("   - 进行正常对话")
        
        input("\n测试完成后按回车停止录音...")
        
        result = recorder.stop_recording()
        if result:
            print(f"\n✅ 录音完成!")
            print(f"📁 麦克风文件: {result['mic_file']}")
            print(f"📁 系统声音文件: {result['speaker_file']}")
            print(f"⏱️  录音时长: {result['duration']:.2f} 秒")
            print(f"\n请播放两个文件验证:")
            print(f"- 麦克风文件应主要包含你的声音")
            print(f"- 系统声音文件应主要包含对方的声音")
        else:
            print("❌ 录音失败")
    else:
        print("❌ 无法开始录音")

if __name__ == "__main__":
    main()