#!/usr/bin/env python3
"""
WASAPI Loopback 测试脚本
测试是否可以不通过立体声混音直接录制系统音频
"""

import sounddevice as sd
import numpy as np
import wave
import time
import sys

def check_environment():
    """检查环境支持情况"""
    print("=== 环境检查 ===")
    print(f"sounddevice版本: {sd.__version__}")
    
    # 检查WASAPI支持
    wasapi_found = False
    wasapi_id = None
    
    print("\n可用的Host APIs:")
    for i, api in enumerate(sd.query_hostapis()):
        print(f"  [{i}] {api['name']}")
        if 'WASAPI' in api['name']:
            wasapi_found = True
            wasapi_id = i
    
    if not wasapi_found:
        print("❌ 未找到WASAPI支持")
        return False, None
    
    print(f"✅ 找到WASAPI: ID={wasapi_id}")
    return True, wasapi_id

def test_wasapi_loopback():
    """测试WASAPI Loopback录制"""
    print("\n=== WASAPI Loopback 测试 ===")
    
    # 检查环境
    wasapi_supported, wasapi_id = check_environment()
    if not wasapi_supported:
        return False
    
    try:
        # 获取WASAPI的默认输出设备
        wasapi_info = sd.query_hostapis()[wasapi_id]
        default_output = wasapi_info['default_output_device']
        
        if default_output < 0:
            print("❌ 没有默认输出设备")
            return False
        
        output_device = sd.query_devices()[default_output]
        print(f"默认输出设备: [{default_output}] {output_device['name']}")
        
        # 尝试方法1: 使用WasapiSettings
        print("\n尝试方法1: WasapiSettings...")
        try:
            # 检查是否有WasapiSettings
            if hasattr(sd, 'WasapiSettings'):
                settings = sd.WasapiSettings(loopback=True)
                print("✅ WasapiSettings可用")
                
                # 测试录制
                duration = 3  # 录制3秒
                samplerate = 44100
                
                print(f"开始录制系统音频 {duration} 秒...")
                print("请播放一些音频（音乐、视频等）来测试...")
                
                recording = sd.rec(
                    int(duration * samplerate),
                    samplerate=samplerate,
                    channels=2,
                    device=default_output,
                    hostapi=wasapi_id,
                    extra_settings=settings
                )
                sd.wait()
                
                # 检查录制结果
                max_amplitude = np.max(np.abs(recording))
                print(f"录制完成，最大音量: {max_amplitude:.4f}")
                
                if max_amplitude > 0.001:  # 有音频信号
                    # 保存测试文件
                    filename = "wasapi_loopback_test.wav"
                    with wave.open(filename, 'wb') as wf:
                        wf.setnchannels(2)
                        wf.setsampwidth(2)
                        wf.setframerate(samplerate)
                        wf.writeframes((recording * 32767).astype(np.int16).tobytes())
                    
                    print(f"✅ 成功录制系统音频！保存为: {filename}")
                    return True
                else:
                    print("⚠️ 录制到音频但音量很小，可能没有播放音频")
                    return True  # 技术上成功了
            else:
                print("❌ WasapiSettings不可用")
        
        except Exception as e:
            print(f"❌ 方法1失败: {e}")
        
        # 尝试方法2: 直接指定loopback参数
        print("\n尝试方法2: 直接参数...")
        try:
            duration = 3
            samplerate = 44100
            
            print(f"开始录制系统音频 {duration} 秒...")
            
            # 尝试不同的参数组合
            recording = sd.rec(
                int(duration * samplerate),
                samplerate=samplerate,
                channels=2,
                device=default_output,
                hostapi=wasapi_id
            )
            sd.wait()
            
            max_amplitude = np.max(np.abs(recording))
            print(f"录制完成，最大音量: {max_amplitude:.4f}")
            
            if max_amplitude > 0.001:
                filename = "wasapi_direct_test.wav"
                with wave.open(filename, 'wb') as wf:
                    wf.setnchannels(2)
                    wf.setsampwidth(2)
                    wf.setframerate(samplerate)
                    wf.writeframes((recording * 32767).astype(np.int16).tobytes())
                
                print(f"✅ 方法2成功！保存为: {filename}")
                return True
            else:
                print("⚠️ 方法2录制到音频但音量很小")
        
        except Exception as e:
            print(f"❌ 方法2失败: {e}")
        
        print("❌ 所有WASAPI Loopback方法都失败")
        return False
        
    except Exception as e:
        print(f"❌ WASAPI测试失败: {e}")
        return False

def fallback_test():
    """回退测试：检查是否有立体声混音"""
    print("\n=== 回退测试：立体声混音 ===")
    
    stereo_mix_keywords = ['stereo mix', '立体声混音', 'what u hear', 'wave out mix']
    
    for i, device in enumerate(sd.query_devices()):
        if device['max_input_channels'] > 0:
            name = device['name'].lower()
            if any(keyword in name for keyword in stereo_mix_keywords):
                print(f"找到立体声混音设备: [{i}] {device['name']}")
                return True
    
    print("❌ 未找到立体声混音设备")
    return False

if __name__ == "__main__":
    print("WASAPI Loopback 测试工具")
    print("=" * 50)
    
    # 主测试
    success = test_wasapi_loopback()
    
    if not success:
        print("\nWASAPI Loopback失败，检查立体声混音...")
        fallback_test()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 测试结果：WASAPI Loopback 可用！")
        print("可以不依赖立体声混音录制系统音频")
    else:
        print("❌ 测试结果：WASAPI Loopback 不可用")
        print("需要启用立体声混音或安装虚拟音频设备")
    
    input("\n按回车键退出...")