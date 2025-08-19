#!/usr/bin/env python3
"""
启动增强版录音系统
"""

import sys
import os
sys.path.append('src')

from src.ui.enhanced_main_window import EnhancedRecorderUI

if __name__ == "__main__":
    print("启动增强版呼叫中心录音系统...")
    app = EnhancedRecorderUI()
    app.run()