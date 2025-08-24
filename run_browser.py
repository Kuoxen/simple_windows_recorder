#!/usr/bin/env python3
"""
浏览器音频录制器启动脚本
只录制来自浏览器的系统音频
"""

import sys
import os
import logging

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config.settings import Settings
from src.ui.browser_recorder_window import BrowserRecorderWindow

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('browser_recorder.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def main():
    """主函数"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # 加载设置
        settings = Settings()
        
        # 创建并启动UI
        app = BrowserRecorderWindow(settings)
        app.run()
        
    except Exception as e:
        logger.error(f"程序启动失败: {e}")
        input("按回车键退出...")

if __name__ == "__main__":
    main()