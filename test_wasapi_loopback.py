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
import os
import inspect

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
    """测试WASAPI Loopback录制（无需立体声混音）"""
    print("\n=== WASAPI Loopback 测试 ===")

    # 检查环境
    wasapi_supported, wasapi_id = check_environment()
    if not wasapi_supported:
        return False

    try:
        # 解析默认输出设备（全局默认优先，其次WASAPI默认）
        devices = sd.query_devices()
        default_output = None
        try:
            default_output = sd.default.device[1]
        except Exception:
            default_output = None
        if default_output is None or default_output < 0:
            api_info = sd.query_hostapis()[wasapi_id]
            default_output = api_info.get('default_output_device', -1)
        if default_output is None or default_output < 0:
            print("❌ 没有默认输出设备")
            return False

        output_device = devices[default_output]
        samplerate = int(output_device.get('default_samplerate') or 44100)
        print(f"默认输出设备: [{default_output}] {output_device['name']} | 采样率: {samplerate}")

        # 方法1: 使用 sounddevice 的 WASAPI loopback（正确用法：extra_settings，不要传 hostapi）
        print("\n尝试方法1: sounddevice + WasapiSettings(loopback=True)...")
        try:
            if hasattr(sd, 'WasapiSettings'):
                has_loopback_param = False
                try:
                    sig = inspect.signature(sd.WasapiSettings)
                    has_loopback_param = 'loopback' in sig.parameters
                except Exception:
                    # 某些版本需要检查 __init__
                    try:
                        sig = inspect.signature(sd.WasapiSettings.__init__)
                        has_loopback_param = 'loopback' in sig.parameters
                    except Exception:
                        has_loopback_param = False

                if has_loopback_param:
                    settings = sd.WasapiSettings(loopback=True)
                    duration = 3
                    frames = int(duration * samplerate)
                    print(f"开始录制系统音频 {duration} 秒（WASAPI Loopback）...")
                    recording = sd.rec(
                        frames,
                        samplerate=samplerate,
                        channels=2,
                        dtype='float32',
                        device=default_output,
                        extra_settings=settings
                    )
                    sd.wait()

                    max_amplitude = float(np.max(np.abs(recording))) if recording is not None else 0.0
                    print(f"录制完成，最大音量: {max_amplitude:.4f}")
                    if max_amplitude > 0.001:
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
                        return True
                else:
                    print("ℹ️ 当前 sounddevice 不支持 WasapiSettings(loopback) 参数")
            else:
                print("ℹ️ 当前 sounddevice 未提供 WasapiSettings 接口")
        except Exception as e:
            print(f"❌ 方法1失败: {e}")

        # 方法2: 不依赖 WasapiSettings，扫描可用的 loopback/混音 输入设备直接录制
        print("\n尝试方法2: 扫描 loopback 输入设备并直接录制...")
        try:
            stereo_mix_keywords = [
                'stereo mix', '立体声混音', 'what u hear', 'wave out mix', 'mix',
                'vb-cable', 'cable input', 'cable output', 'voicemeeter', 'virtual cable',
                'loopback'  # 不是必须，但有些设备会包含
            ]
            candidate_id = None
            for i, dev in enumerate(devices):
                name = str(dev.get('name', '')).lower()
                if dev.get('max_input_channels', 0) > 0 and any(k in name for k in stereo_mix_keywords):
                    candidate_id = i
                    break
            if candidate_id is not None:
                print(f"找到可能的系统音频输入设备: [{candidate_id}] {devices[candidate_id]['name']}")
                duration = 3
                frames = int(duration * samplerate)
                print(f"开始录制系统音频 {duration} 秒（直接输入设备）...")
                recording = sd.rec(
                    frames,
                    samplerate=samplerate,
                    channels=2,
                    dtype='float32',
                    device=candidate_id
                )
                sd.wait()

                max_amplitude = float(np.max(np.abs(recording))) if recording is not None else 0.0
                print(f"录制完成，最大音量: {max_amplitude:.4f}")
                if max_amplitude > 0.001:
                    filename = "wasapi_device_scan_test.wav"
                    with wave.open(filename, 'wb') as wf:
                        wf.setnchannels(2)
                        wf.setsampwidth(2)
                        wf.setframerate(samplerate)
                        wf.writeframes((recording * 32767).astype(np.int16).tobytes())
                    print(f"✅ 方法2成功！保存为: {filename}")
                    return True
                else:
                    print("⚠️ 方法2录制到音频但音量很小")
            else:
                print("❌ 未找到可用的 loopback/立体声混音 输入设备")
        except Exception as e:
            print(f"❌ 方法2失败: {e}")

        # 方法3: 使用 PyAudioWPatch 的 WASAPI loopback（无需立体声混音/虚拟设备）
        print("\n尝试方法3: 使用 PyAudioWPatch WASAPI Loopback...")
        try:
            try:
                import pyaudiowpatch as pyaudio
                print(f"PyAudioWPatch 版本: {getattr(pyaudio, '__version__', 'unknown')}")
            except Exception as e_imp:
                print(f"❌ 无法导入 PyAudioWPatch: {e_imp!r}")
                raise

            p = None
            stream = None
            duration = 3
            frames_collected = []

            try:
                p = pyaudio.PyAudio()
                loop_info = None
                try:
                    loop_info = p.get_default_wasapi_loopback()
                    print(f"默认WASAPI Loopback设备: index={loop_info.get('index')} name={loop_info.get('name')}")
                except Exception as e_def:
                    print(f"⚠️ 获取默认 loopback 设备失败: {e_def!r}")

                if not loop_info:
                    # 扫描 isLoopback 设备
                    for i in range(p.get_device_count()):
                        info = p.get_device_info_by_index(i)
                        if info.get('isLoopback') and info.get('maxInputChannels', 0) > 0:
                            loop_info = info
                            print(f"发现 loopback 设备: index={info.get('index')} name={info.get('name')}")
                            break

                if not loop_info:
                    print("❌ 未找到任何 WASAPI loopback 设备")
                    raise RuntimeError("no_wasapi_loopback_device")

                device_index = int(loop_info['index'])
                channels = int(loop_info.get('maxInputChannels', 2) or 2)
                rate = int(samplerate or int(loop_info.get('defaultSampleRate', 44100)))

                def _on_frames(in_data, frame_count, time_info, status):
                    if in_data:
                        audio = np.frombuffer(in_data, dtype=np.int16).astype(np.float32) / 32768.0
                        if channels > 1 and len(audio) % channels == 0:
                            audio = audio.reshape(-1, channels).mean(axis=1)
                        frames_collected.append((audio * 32767).astype(np.int16).tobytes())
                    return (None, pyaudio.paContinue)

                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=channels,
                    rate=rate,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=1024,
                    stream_callback=_on_frames,
                )
                stream.start_stream()
                print(f"开始录制系统音频 {duration} 秒（PyAudioWPatch）...")
                time.sleep(duration)
            except Exception as e_start:
                print(f"❌ PyAudioWPatch 录制启动失败: {e_start!r}")
            finally:
                try:
                    if stream and stream.is_active():
                        stream.stop_stream()
                except Exception:
                    pass
                try:
                    if stream:
                        stream.close()
                except Exception:
                    pass
                try:
                    if p:
                        p.terminate()
                except Exception:
                    pass

            if frames_collected:
                filename = "wasapi_pyaudio_test.wav"
                with wave.open(filename, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(samplerate)
                    wf.writeframes(b''.join(frames_collected))
                print(f"✅ 方法3成功！保存为: {filename}")
                return True
            else:
                print("⚠️ 方法3未采集到音频帧")
        except Exception as e:
            print(f"❌ 方法3失败: {e}")

        # 方法4: 使用项目内置的底层 WASAPI 录制器（无需立体声混音）
        print("\n尝试方法4: 使用内置 WASAPIRecorder（底层WASAPI Loopback）...")
        try:
            sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
            from audio.wasapi_recorder import WASAPIRecorder

            duration = 3
            samplerate = samplerate or 44100
            recorder = WASAPIRecorder(sample_rate=samplerate)
            frames_collected = []

            def on_audio(chunk: np.ndarray):
                # chunk 为单声道 float32
                frames_collected.append((chunk * 32767).astype(np.int16).tobytes())

            recorder.set_audio_callback(on_audio)
            if not recorder.start_recording():
                print("❌ WASAPIRecorder 启动失败")
            else:
                print(f"开始录制系统音频 {duration} 秒（WASAPIRecorder）...")
                time.sleep(duration)
                recorder.stop_recording()

                if frames_collected:
                    filename = "wasapi_lowlevel_test.wav"
                    with wave.open(filename, 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(samplerate)
                        wf.writeframes(b''.join(frames_collected))
                    print(f"✅ 方法3成功！保存为: {filename}")
                    return True
                else:
                    print("⚠️ 方法3未采集到音频帧")
        except Exception as e:
            print(f"❌ 方法4失败: {e}")

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