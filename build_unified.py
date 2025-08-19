#!/usr/bin/env python3
"""
统一录制系统打包脚本
"""

import PyInstaller.__main__
import os
import sys

def build_unified():
    """打包统一录制系统"""
    
    # 获取项目根目录
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # 打包参数
    args = [
        'run_unified.py',
        '--name=岩硅智能音频采集器-统一版',
        '--windowed',
        '--onefile',
        '--icon=icon.ico' if os.path.exists('icon.ico') else '',
        f'--add-data={os.path.join(project_root, "config.yaml")};.',
        f'--add-data={os.path.join(project_root, "src")};src',
        '--hidden-import=sounddevice',
        '--hidden-import=numpy',
        '--hidden-import=wave',
        '--hidden-import=yaml',
        '--hidden-import=requests',
        '--hidden-import=oss2',
        '--clean',
        '--noconfirm'
    ]
    
    # 过滤空参数
    args = [arg for arg in args if arg]
    
    print("开始打包统一录制系统...")
    print(f"参数: {args}")
    
    try:
        PyInstaller.__main__.run(args)
        print("✅ 打包完成！")
        print("📁 可执行文件位于 dist/ 目录")
    except Exception as e:
        print(f"❌ 打包失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    build_unified()