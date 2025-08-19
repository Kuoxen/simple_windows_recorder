#!/usr/bin/env python3
"""
增强版打包脚本
"""

import os
import subprocess
import sys

def build_enhanced_exe():
    print("开始打包增强版呼叫中心录音系统...")
    
    separator = ":" if os.name != 'nt' else ";"
    
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",  # 改为窗口模式，更专业
        "--name=呼叫中心录音系统-增强版",
        f"--add-data=config.yaml{separator}.",
        f"--add-data=src{separator}src",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=requests",
        "--hidden-import=numpy",
        "--hidden-import=sounddevice",
        "--hidden-import=yaml",
        "--hidden-import=oss2",
        "--hidden-import=logging",  # 新增
        # 原版模块
        "--hidden-import=src.config.settings",
        "--hidden-import=src.audio.recorder",
        "--hidden-import=src.audio.device_manager",
        "--hidden-import=src.ui.main_window",
        "--hidden-import=src.storage.uploader",
        # 增强版模块
        "--hidden-import=src.audio.enhanced_device_manager",
        "--hidden-import=src.audio.enhanced_recorder", 
        "--hidden-import=src.ui.enhanced_main_window",
        "run_enhanced.py"  # 使用增强版入口
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ 增强版打包成功！")
        if os.name == 'nt':
            print("📁 可执行文件: dist/呼叫中心录音系统-增强版.exe")
        else:
            print("📁 可执行文件: dist/呼叫中心录音系统-增强版")
        
        print("\n🚀 使用说明:")
        print("1. 将生成的exe文件复制到目标电脑")
        print("2. 确保目标电脑已安装VB-Cable或启用立体声混音")
        print("3. 双击运行，程序会自动检测和推荐最佳设备")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 打包失败: {e}")
        print(f"错误输出: {e.stderr}")
        
    except FileNotFoundError:
        print("❌ 未找到 pyinstaller")
        print("请先安装: pip install pyinstaller")

if __name__ == "__main__":
    build_enhanced_exe()