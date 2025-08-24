#!/usr/bin/env python3
"""
浏览器音频录制系统启动脚本 - 基于unified版本改造
支持手动录制和自动录制模式切换，专门针对浏览器音频采集
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config.settings import Settings
from ui.browser_recorder_window import BrowserRecorderWindow

def main():
    """主函数"""
    try:
        # 加载设置
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        settings = Settings(config_path)
        
        # 创建并启动UI
        app = BrowserRecorderWindow(settings)
        app.run()
        
    except Exception as e:
        print(f"程序启动失败: {e}")
        input("按回车键退出...")

if __name__ == "__main__":
    main()