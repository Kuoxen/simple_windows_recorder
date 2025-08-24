#!/usr/bin/env python3
"""
浏览器音频录制系统打包脚本
"""

import os
import subprocess
import sys

def build_browser_unified_exe():
    print("开始打包浏览器音频录制系统...")
    
    separator = ":" if os.name != 'nt' else ";"
    
    cmd = [
        "pyinstaller",
        "--onefile",
        "--console",
        "--name=岩硅浏览器音频采集器",
        f"--add-data=config.yaml{separator}.",
        f"--add-data=src{separator}src",
        "--icon=icon.ico",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=requests",
        "--hidden-import=numpy",
        "--hidden-import=sounddevice",
        "--hidden-import=yaml",
        "--hidden-import=oss2",
        "--hidden-import=logging",
        "--hidden-import=psutil",
        "--hidden-import=ctypes",
        "--hidden-import=src.config.settings",
        "--hidden-import=src.audio.browser_audio_recorder",
        "--hidden-import=src.audio.wasapi_recorder",
        "--hidden-import=src.audio.enhanced_device_manager",
        "--hidden-import=src.ui.browser_recorder_window",
        "--hidden-import=src.storage.uploader",
        "--hidden-import=src.audio.circular_buffer",
        "--hidden-import=src.audio.activity_detector",
        "--hidden-import=src.audio.post_processor",
        "--hidden-import=src.ui.device_calibration_window",
        "run_browser_unified.py"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ 浏览器音频录制系统打包成功！")
        if os.name == 'nt':
            print("📁 可执行文件: dist/岩硅浏览器音频采集器.exe")
        else:
            print("📁 可执行文件: dist/岩硅浏览器音频采集器")
        
        print("\n🚀 使用说明:")
        print("1. 将生成的exe文件复制到目标电脑")
        print("2. Windows系统：自动使用WASAPI采集浏览器音频，无需额外配置")
        print("3. macOS/Linux系统：仅支持麦克风录制，浏览器音频采集不可用")
        print("4. 双击运行，可在手动和自动录制模式间切换")
        print("5. 启用自动上传：修改config.yaml中upload.enabled=true")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 浏览器音频录制系统打包失败: {e}")
        print(f"错误输出: {e.stderr}")
        
    except FileNotFoundError:
        print("❌ 未找到 pyinstaller")
        print("请先安装: pip install pyinstaller")

if __name__ == "__main__":
    build_browser_unified_exe()