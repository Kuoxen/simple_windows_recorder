#!/usr/bin/env python3
"""
打包脚本 - 将Python程序打包成独立的可执行文件
"""

import os
import subprocess
import sys

def build_exe():
    print("开始打包呼叫中心录音系统...")
    
    # 根据操作系统选择路径分隔符
    separator = ":" if os.name != 'nt' else ";"
    
    # PyInstaller 命令
    cmd = [
        "pyinstaller",
        "--onefile",                    # 打包成单个文件
        "--windowed",                   # 不显示控制台窗口
        "--name=呼叫中心录音系统",        # 程序名称
        f"--add-data=config.yaml{separator}.",     # 包含配置文件
        f"--add-data=src{separator}src",           # 包含src目录
        "--hidden-import=tkinter",      # 确保包含tkinter
        "--hidden-import=tkinter.ttk",  # 确保包含ttk
        "--hidden-import=src.config.settings",     # 明确指定模块
        "--hidden-import=src.audio.recorder",      # 明确指定模块
        "--hidden-import=src.audio.device_manager", # 明确指定模块
        "--hidden-import=src.ui.main_window",      # 明确指定模块
        "run_ui.py"                     # 主程序文件
    ]
    
    try:
        # 执行打包命令
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("打包成功！")
        if os.name == 'nt':
            print("可执行文件位置: dist/呼叫中心录音系统.exe")
        else:
            print("可执行文件位置: dist/呼叫中心录音系统")
        
    except subprocess.CalledProcessError as e:
        print(f"打包失败: {e}")
        print(f"错误输出: {e.stderr}")
        
    except FileNotFoundError:
        print("错误: 未找到 pyinstaller")
        print("请先安装: pip install pyinstaller")

if __name__ == "__main__":
    build_exe()