#!/usr/bin/env python3
"""
设备校准功能测试脚本
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import tkinter as tk
from src.ui.device_calibration_window import DeviceCalibrationWindow

def test_calibration():
    """测试设备校准功能"""
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    def on_calibration_complete(mic_id, system_id):
        print(f"校准完成!")
        print(f"推荐麦克风设备: {mic_id}")
        print(f"推荐系统音频设备: {system_id}")
        root.quit()
    
    # 打开校准窗口
    calibration_window = DeviceCalibrationWindow(root, on_calibration_complete)
    
    root.mainloop()

if __name__ == "__main__":
    print("设备校准功能测试")
    print("=" * 50)
    test_calibration()