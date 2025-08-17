#!/usr/bin/env python3
"""
启动桌面UI应用
"""

import sys
import os
sys.path.append('src')

from src.ui.main_window import RecorderUI

if __name__ == "__main__":
    app = RecorderUI()
    app.run()