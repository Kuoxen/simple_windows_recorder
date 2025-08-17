#!/usr/bin/env python3
"""
音频会话录制测试
尝试所有可能的loopback设备
"""

import sys
import os
sys.path.append('src')

from src.config.settings import Settings
from src.audio.audio_session_recorder import AudioSessionRecorder

def main():
    print("=== 音频会话录制测试 ===")
    
    settings = Settings("config.yaml")
    recorder = AudioSessionRecorder(settings)
    
    # 获取所有候选设备
    candidates = recorder.get_all_loopback_candidates()
    
    print("找到的回环候选设备:")
    for i, (device_id, device_info) in enumerate(candidates):
        print(f"  {i}: [{device_id}] {device_info['name']}")
    
    if not candidates:
        print("❌ 未找到任何回环设备候选")
        return
    
    # 让用户选择设备测试
    print(f"\n选择要测试的设备 (0-{len(candidates)-1}):")
    choice = input("输入序号 (回车测试第一个): ").strip()
    
    if choice.isdigit() and 0 <= int(choice) < len(candidates):
        selected_device = candidates[int(choice)][0]
    else:
        selected_device = candidates[0][0]
    
    selected_name = next(d[1]['name'] for d in candidates if d[0] == selected_device)
    print(f"将测试设备: [{selected_device}] {selected_name}")
    
    print(f"\n=== 测试说明 ===")
    print("1. 确保你正在使用蓝牙耳机")
    print("2. 准备播放一些音频")
    print("3. 我们会尝试从选定的设备录制系统音频")
    
    input("\n按回车开始录音...")
    
    if recorder.start_recording(force_loopback_device=selected_device):
        print("\n🎙️  录音中...")
        print("💡 现在请:")
        print("   1. 对着麦克风说话")
        print("   2. 播放音频（音乐、视频等）")
        print("   3. 观察是否能录制到系统音频")
        
        input("\n测试完成后按回车停止录音...")
        
        result = recorder.stop_recording()
        if result:
            print(f"\n✅ 录音完成!")
            print(f"📁 麦克风文件: {result['mic_file']}")
            print(f"📁 系统音频文件: {result['system_file']}")
            print(f"⏱️  录音时长: {result['duration']:.2f} 秒")
            
            # 检查系统音频文件
            if result['system_file'] and os.path.exists(result['system_file']):
                size = os.path.getsize(result['system_file'])
                print(f"📊 系统音频文件大小: {size} 字节")
                if size < 1000:
                    print("⚠️  系统音频文件很小，可能没有录到声音")
                    print("💡 建议:")
                    print("   - 尝试其他候选设备")
                    print("   - 或者切换到本地扬声器输出测试")
                else:
                    print("✅ 系统音频录制成功！")
                    
                    # 询问是否要测试其他设备
                    if len(candidates) > 1:
                        test_more = input("\n是否测试其他设备? (y/n): ").strip().lower()
                        if test_more == 'y':
                            main()  # 递归调用重新测试
            else:
                print("❌ 系统音频录制失败")
        else:
            print("❌ 录音失败")
    else:
        print("❌ 无法开始录音")

if __name__ == "__main__":
    main()