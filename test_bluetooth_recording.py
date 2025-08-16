#!/usr/bin/env python3
"""
蓝牙音频录制测试
尝试不同的方法录制蓝牙音频输出
"""

import sys
import os
sys.path.append('src')

from src.config.settings import Settings
from src.audio.device_manager import DeviceManager
from src.audio.recorder import AudioRecorder

def main():
    print("=== 蓝牙音频录制测试 ===")
    
    settings = Settings("config.yaml")
    device_manager = DeviceManager()
    device_manager.print_devices()
    
    # 查找蓝牙相关设备
    bluetooth_devices = []
    for i, device in enumerate(device_manager.devices):
        name = device['name'].lower()
        if any(keyword in name for keyword in ['accentum', 'bluetooth', '耳机', 'headphone']):
            if device['max_input_channels'] > 0:  # 只要输入设备
                bluetooth_devices.append((i, device))
    
    print(f"\n=== 蓝牙相关输入设备 ===")
    for i, (idx, device) in enumerate(bluetooth_devices):
        print(f"[{i}] [{idx}] {device['name']}")
    
    # 立体声混音
    loopback_device = device_manager.get_loopback_device()
    print(f"\n立体声混音设备: [{loopback_device}] {device_manager.devices[loopback_device]['name']}")
    
    print(f"\n=== 测试方案 ===")
    print("1. 方案A: 使用立体声混音 + 本地扬声器")
    print("2. 方案B: 尝试蓝牙设备输入")
    print("3. 方案C: 同时录制多个设备")
    
    choice = input("选择测试方案 (1/2/3): ").strip()
    
    recorder = AudioRecorder(settings)
    
    if choice == "1":
        print("\n请切换到本地扬声器输出，然后播放音频测试")
        input("切换完成后按回车开始录音...")
        recorder.start_recording(None, loopback_device)
        
    elif choice == "2":
        if bluetooth_devices:
            bt_device = bluetooth_devices[0][0]  # 使用第一个蓝牙设备
            print(f"使用蓝牙设备: [{bt_device}] {device_manager.devices[bt_device]['name']}")
            input("按回车开始录音...")
            recorder.start_recording(None, bt_device)
        else:
            print("未找到蓝牙输入设备")
            return
            
    elif choice == "3":
        print("同时测试立体声混音和蓝牙设备")
        input("按回车开始录音...")
        # 这里需要修改recorder支持多设备录制
        recorder.start_recording(None, loopback_device)
    
    else:
        print("无效选择")
        return
    
    print("\n🎙️  录音中... 播放一些音频测试")
    input("测试完成后按回车停止...")
    
    result = recorder.stop_recording()
    if result:
        print(f"\n✅ 录音完成!")
        print(f"📁 系统声音文件: {result['speaker_file']}")
        print(f"⏱️  录音时长: {result['duration']:.2f} 秒")
        
        # 检查文件大小
        if os.path.exists(result['speaker_file']):
            size = os.path.getsize(result['speaker_file'])
            print(f"📊 文件大小: {size} 字节")
            if size < 1000:
                print("⚠️  文件很小，可能没有录到声音")
            else:
                print("✅ 文件大小正常，应该有声音")

if __name__ == "__main__":
    main()