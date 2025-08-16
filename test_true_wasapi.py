#!/usr/bin/env python3
"""
真正的 WASAPI 测试
测试 PyAudio 的 WASAPI loopback 功能
"""

import sys
import os
sys.path.append('src')

from src.config.settings import Settings
from src.audio.true_wasapi_recorder import TrueWASAPIRecorder

def main():
    print("=== 真正的 WASAPI Loopback 测试 ===")
    print("这个测试使用 PyAudio 直接访问 WASAPI")
    print("应该能录制任何输出设备的音频，包括蓝牙耳机")
    
    settings = Settings("config.yaml")
    recorder = TrueWASAPIRecorder(settings)
    
    # 显示 WASAPI 设备
    recorder.print_wasapi_devices()
    
    print(f"\n=== 测试说明 ===")
    print("1. 确保你的音频正在播放")
    print("2. 无论使用什么输出设备（蓝牙耳机、扬声器等）")
    print("3. WASAPI loopback 应该都能录制到")
    
    input("\n按回车开始录音...")
    
    if recorder.start_recording():
        print("\n🎙️  WASAPI 录音中...")
        print("💡 现在请:")
        print("   1. 对着麦克风说话")
        print("   2. 播放音频（确保有声音输出）")
        print("   3. 测试不同的输出设备")
        
        input("\n测试完成后按回车停止录音...")
        
        result = recorder.stop_recording()
        if result:
            print(f"\n✅ WASAPI 录音完成!")
            print(f"📁 麦克风文件: {result['mic_file']}")
            print(f"📁 系统音频文件: {result['system_file']}")
            print(f"⏱️  录音时长: {result['duration']:.2f} 秒")
            
            # 检查系统音频文件
            if result['system_file'] and os.path.exists(result['system_file']):
                size = os.path.getsize(result['system_file'])
                print(f"📊 系统音频文件大小: {size} 字节")
                if size < 1000:
                    print("⚠️  系统音频文件很小")
                    print("💡 可能的原因:")
                    print("   - 没有音频在播放")
                    print("   - WASAPI loopback 设备不可用")
                    print("   - 需要管理员权限")
                else:
                    print("✅ 系统音频录制成功！")
                    print("🎉 这意味着可以录制任何输出设备的音频")
            else:
                print("❌ 系统音频录制失败")
        else:
            print("❌ 录音失败")
    else:
        print("❌ 无法开始录音")

if __name__ == "__main__":
    main()