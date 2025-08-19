#!/usr/bin/env python3
"""
自动录制版本启动脚本
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ui.auto_recorder_window import AutoRecorderUI

if __name__ == "__main__":
    app = AutoRecorderUI()
    app.run()