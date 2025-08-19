#!/usr/bin/env python3
"""
统一版打包脚本
"""

import os
import subprocess
import sys

def build_unified_exe():
    print("开始打包统一版智能录音系统...")
    
    separator = ":" if os.name != 'nt' else ";"
    
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=智能录音系统-统一版",
        f"--add-data=config.yaml{separator}.",
        f"--add-data=src{separator}src",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=requests",
        "--hidden-import=numpy",
        "--hidden-import=sounddevice",
        "--hidden-import=yaml",
        "--hidden-import=oss2",
        "--hidden-import=logging",
        "--hidden-import=src.config.settings",
        "--hidden-import=src.audio.recorder",
        "--hidden-import=src.audio.device_manager",
        "--hidden-import=src.ui.main_window",
        "--hidden-import=src.storage.uploader",
        "--hidden-import=src.audio.enhanced_device_manager",
        "--hidden-import=src.audio.enhanced_recorder", 
        "--hidden-import=src.ui.enhanced_main_window",
        "--hidden-import=src.audio.circular_buffer",
        "--hidden-import=src.audio.activity_detector",
        "--hidden-import=src.audio.auto_recorder",
        "--hidden-import=src.ui.auto_recorder_window",
        "--hidden-import=src.ui.unified_recorder_window",
        "run_unified.py"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ 智能录音系统-统一版打包成功！")
        if os.name == 'nt':
            print("📁 可执行文件: dist/智能录音系统-统一版.exe")
        else:
            print("📁 可执行文件: dist/智能录音系统-统一版")
        
        print("\n🚀 使用说明:")
        print("1. 将生成的exe文件复制到目标电脑")
        print("2. 确保目标电脑已安装VB-Cable或启用立体声混音")
        print("3. 双击运行，可在手动和自动录制模式间切换")
        print("4. 系统日志在界面底部显示，无控制台窗口")
        print("5. 启用自动上传：修改config.yaml中upload.enabled=true")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 智能录音系统-统一版打包失败: {e}")
        print(f"错误输出: {e.stderr}")
        
    except FileNotFoundError:
        print("❌ 未找到 pyinstaller")
        print("请先安装: pip install pyinstaller")

if __name__ == "__main__":
    build_unified_exe()