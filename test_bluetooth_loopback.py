#!/usr/bin/env python3
"""
蓝牙 Loopback 设备检测
专门查找蓝牙设备的loopback输入版本
"""

import sys
import os
sys.path.append('src')

import sounddevice as sd
from src.config.settings import Settings
from src.audio.recorder import AudioRecorder

def find_bluetooth_loopback():
    """查找蓝牙设备的loopback版本"""
    devices = sd.query_devices()
    
    # 找到当前默认输出设备
    default_output = sd.default.device[1]
    output_device = devices[default_output]
    
    print(f"当前默认输出设备: [{default_output}] {output_device['name']}")
    
    # 查找所有包含相同关键词的输入设备
    output_keywords = output_device['name'].lower().split()
    bluetooth_inputs = []
    
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:  # 只看输入设备
            device_name = device['name'].lower()
            
            # 检查是否包含输出设备的关键词
            for keyword in output_keywords:
                if len(keyword) > 3 and keyword in device_name:  # 忽略太短的词
                    bluetooth_inputs.append((i, device, keyword))
                    break
    
    print(f"\n找到的相关输入设备:")
    for i, (device_id, device_info, matched_keyword) in enumerate(bluetooth_inputs):
        print(f"  {i}: [{device_id}] {device_info['name']} (匹配: {matched_keyword})")
    
    return bluetooth_inputs

def test_device(device_id, device_name):
    """测试指定设备是否能录制音频"""
    print(f"\n=== 测试设备 [{device_id}] {device_name} ===")
    
    settings = Settings("config.yaml")
    recorder = AudioRecorder(settings)
    
    print("准备测试这个设备是否能录制系统音频...")
    input("请确保有音频在播放，然后按回车开始录音...")
    
    # 强制使用指定设备作为扬声器录制设备
    if recorder.start_recording(None, device_id):
        print("🎙️  录音中... (10秒)")
        import time
        time.sleep(10)  # 录音10秒
        
        result = recorder.stop_recording()
        if result and result['speaker_file']:
            size = os.path.getsize(result['speaker_file'])
            print(f"📊 录音文件大小: {size} 字节")
            
            if size > 1000:
                print("✅ 成功！这个设备能录制到音频")
                return True
            else:
                print("❌ 失败：文件太小，没有录到音频")
                return False
        else:
            print("❌ 失败：无法创建录音文件")
            return False
    else:
        print("❌ 失败：无法开始录音")
        return False

def main():
    print("=== 蓝牙 Loopback 设备检测 ===")
    
    # 查找蓝牙相关的输入设备
    bluetooth_inputs = find_bluetooth_loopback()
    
    if not bluetooth_inputs:
        print("\n❌ 未找到蓝牙相关的输入设备")
        print("💡 这意味着你的蓝牙耳机没有对应的loopback输入设备")
        print("💡 建议使用虚拟音频设备或切换到本地扬声器")
        return
    
    print(f"\n找到 {len(bluetooth_inputs)} 个候选设备，开始逐个测试...")
    
    working_devices = []
    
    for i, (device_id, device_info, keyword) in enumerate(bluetooth_inputs):
        print(f"\n--- 测试 {i+1}/{len(bluetooth_inputs)} ---")
        if test_device(device_id, device_info['name']):
            working_devices.append((device_id, device_info))
    
    print(f"\n=== 测试结果 ===")
    if working_devices:
        print("✅ 找到可用的蓝牙loopback设备:")
        for device_id, device_info in working_devices:
            print(f"  [{device_id}] {device_info['name']}")
        print("\n🎉 你可以使用这些设备录制蓝牙音频！")
    else:
        print("❌ 没有找到可用的蓝牙loopback设备")
        print("💡 建议:")
        print("   1. 使用VB-Cable等虚拟音频设备")
        print("   2. 录音时切换到本地扬声器")
        print("   3. 检查蓝牙驱动是否支持loopback")

if __name__ == "__main__":
    main()