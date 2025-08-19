#!/usr/bin/env python3
"""
统一录制系统启动脚本
支持手动录制和自动录制模式切换
"""

import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ui.unified_recorder_window import UnifiedRecorderUI

if __name__ == "__main__":
    app = UnifiedRecorderUI()
    app.run()