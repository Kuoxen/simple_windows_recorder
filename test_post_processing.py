#!/usr/bin/env python3
"""测试后处理功能"""

import os
import sys
import numpy as np
import wave
import time
from datetime import datetime

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config.settings import Settings
from audio.post_processor import AudioPostProcessor

def create_test_audio(filename, duration=10, sample_rate=44100, frequency=440, amplitude=0.5):
    """创建测试音频文件"""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = amplitude * np.sin(2 * np.pi * frequency * t)
    
    # 转换为int16
    audio_int16 = (audio_data * 32767).astype(np.int16)
    
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    
    print(f"创建测试音频: {filename}")

def create_silent_audio(filename, duration=10, sample_rate=44100):
    """创建静音测试文件"""
    audio_data = np.zeros(int(sample_rate * duration), dtype=np.float32)
    audio_int16 = (audio_data * 32767).astype(np.int16)
    
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    
    print(f"创建静音音频: {filename}")

def test_post_processing():
    """测试后处理功能"""
    print("=== 测试音频后处理功能 ===")
    
    # 初始化设置和后处理器
    settings = Settings("config.yaml")
    processor = AudioPostProcessor(settings)
    processor.start()
    
    # 创建测试目录
    test_dir = "./test_recordings"
    os.makedirs(test_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # 测试1: 正常录音（双路都有声音）
        print("\n--- 测试1: 正常录音 ---")
        mic_file1 = os.path.join(test_dir, f"mic_{timestamp}_test1.wav")
        system_file1 = os.path.join(test_dir, f"system_{timestamp}_test1.wav")
        
        create_test_audio(mic_file1, duration=10, frequency=440)  # 麦克风：440Hz
        create_test_audio(system_file1, duration=10, frequency=880)  # 系统：880Hz
        
        call_info1 = {
            'agent_phone': '13800138000',
            'customer_name': '张三',
            'customer_id': '12345'
        }
        
        processor.submit_recording(mic_file1, system_file1, call_info1)
        
        # 测试2: 时长过短的录音
        print("\n--- 测试2: 时长过短录音 ---")
        mic_file2 = os.path.join(test_dir, f"mic_{timestamp}_test2.wav")
        system_file2 = os.path.join(test_dir, f"system_{timestamp}_test2.wav")
        
        create_test_audio(mic_file2, duration=2, frequency=440)  # 只有2秒
        create_test_audio(system_file2, duration=2, frequency=880)
        
        call_info2 = {
            'agent_phone': '13800138001',
            'customer_name': '李四',
            'customer_id': '12346'
        }
        
        processor.submit_recording(mic_file2, system_file2, call_info2)
        
        # 测试3: 单侧静音录音
        print("\n--- 测试3: 单侧静音录音 ---")
        mic_file3 = os.path.join(test_dir, f"mic_{timestamp}_test3.wav")
        system_file3 = os.path.join(test_dir, f"system_{timestamp}_test3.wav")
        
        create_test_audio(mic_file3, duration=10, frequency=440)  # 麦克风有声音
        create_silent_audio(system_file3, duration=10)  # 系统音频静音
        
        call_info3 = {
            'agent_phone': '13800138002',
            'customer_name': '王五',
            'customer_id': '12347'
        }
        
        processor.submit_recording(mic_file3, system_file3, call_info3)
        
        # 等待处理完成
        print("\n等待后处理完成...")
        time.sleep(15)
        
        # 检查结果
        print("\n=== 处理结果检查 ===")
        recordings_dir = settings.recording['output_dir']
        files = os.listdir(recordings_dir)
        merged_files = [f for f in files if f.startswith('merged_')]
        
        print(f"生成的合并文件数量: {len(merged_files)}")
        for f in merged_files:
            print(f"  - {f}")
        
        # 预期结果：只有测试1应该生成合并文件
        if len(merged_files) == 1:
            print("✅ 测试通过：只有有效录音生成了合并文件")
        else:
            print(f"❌ 测试失败：预期1个合并文件，实际{len(merged_files)}个")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        processor.stop()
        print("\n后处理器已停止")

if __name__ == "__main__":
    test_post_processing()