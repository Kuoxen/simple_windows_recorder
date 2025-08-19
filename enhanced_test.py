#!/usr/bin/env python3
"""
增强版录音测试脚本
使用改进的设备管理器和录音器进行测试
"""

import sys
import os
import logging
sys.path.append('src')

from src.config.settings import Settings
from src.audio.enhanced_device_manager import EnhancedDeviceManager
from src.audio.enhanced_recorder import EnhancedAudioRecorder

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    print("=== 增强版呼叫中心录音测试 ===")
    
    try:
        # 加载配置
        settings = Settings("config.yaml")
        
        # 使用增强版设备管理器
        device_manager = EnhancedDeviceManager()
        device_manager.print_devices()
        
        # 获取推荐设备
        recommendations = device_manager.get_recommended_devices()
        print(f"\n🎯 推荐设备配置:")
        print(f"   麦克风: {recommendations['microphone']}")
        print(f"   系统音频: {recommendations['system_audio']}")
        
        # 让用户确认或选择设备
        mic_device = recommendations['microphone']
        system_device = recommendations['system_audio']
        
        # 用户可以手动选择设备
        print(f"\n请确认设备选择:")
        if mic_device is not None:
            device_info = device_manager.get_device_info(mic_device)
            print(f"麦克风: [{mic_device}] {device_info['name'] if device_info else 'Unknown'}")
        else:
            print("⚠️  未找到合适的麦克风设备")
            
        if system_device is not None:
            device_info = device_manager.get_device_info(system_device)
            print(f"系统音频: [{system_device}] {device_info['name'] if device_info else 'Unknown'}")
        else:
            print("⚠️  未找到合适的系统音频设备")
            print("💡 建议:")
            print("   1. 安装 VB-Cable (https://vb-audio.com/Cable/)")
            print("   2. 或启用 Windows 立体声混音功能")
        
        # 询问是否继续
        if mic_device is None and system_device is None:
            print("\n❌ 没有可用的录音设备，无法进行测试")
            return
        
        choice = input(f"\n是否使用推荐设备进行测试? (y/n): ").strip().lower()
        if choice != 'y':
            print("测试已取消")
            return
        
        # 创建增强版录音器
        recorder = EnhancedAudioRecorder(settings)
        
        # 设置状态回调
        def status_callback(message):
            print(f"[状态] {message}")
        
        recorder.set_status_callback(status_callback)
        
        print("\n=== 录音测试说明 ===")
        print("1. 确保已正确配置音频设备")
        print("2. 如果测试系统音频，请播放一些音乐或视频")
        print("3. 按回车开始录音")
        print("4. 测试完成后按回车停止")
        
        input("\n准备好后按回车开始录音...")
        
        # 开始录音
        if recorder.start_recording(mic_device, system_device):
            print("\n🎙️  录音进行中...")
            print("💡 现在可以:")
            print("   - 对着麦克风说话 (测试麦克风)")
            print("   - 播放音乐/视频 (测试系统音频)")
            
            # 显示实时状态
            import time
            start_time = time.time()
            try:
                while True:
                    time.sleep(1)
                    status = recorder.get_recording_status()
                    if status['recording']:
                        duration = int(status['duration'])
                        mic_data = status['mic_data_length']
                        speaker_data = status['speaker_data_length']
                        print(f"\r⏱️  录音时长: {duration}s | 麦克风数据: {mic_data} | 系统音频数据: {speaker_data}", end='', flush=True)
                    else:
                        break
            except KeyboardInterrupt:
                print(f"\n\n用户中断录音")
            
            print(f"\n\n停止录音中...")
            result = recorder.stop_recording()
            
            if result:
                print(f"\n✅ 录音测试完成!")
                print(f"⏱️  总时长: {result['duration']:.2f} 秒")
                
                if result['mic_success']:
                    print(f"🎤 麦克风文件: {result['mic_file']}")
                else:
                    print(f"❌ 麦克风录音失败")
                
                if result['speaker_success']:
                    print(f"🔊 系统音频文件: {result['speaker_file']}")
                else:
                    print(f"❌ 系统音频录音失败")
                
                if result['errors']:
                    print(f"\n⚠️  错误信息:")
                    for error in result['errors']:
                        print(f"   - {error}")
                
                print(f"\n📁 录音文件保存在: {settings.recording['output_dir']}")
                print(f"💡 请播放录音文件验证效果")
                
            else:
                print("❌ 录音失败")
        else:
            print("❌ 无法开始录音")
    
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()