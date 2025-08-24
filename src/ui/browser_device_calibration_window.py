import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import numpy as np
import sounddevice as sd
from typing import List, Tuple, Callable, Optional

class BrowserDeviceCalibrationWindow:
    """浏览器版设备校准窗口 - 只测试麦克风"""
    
    def __init__(self, parent, mic_devices: List[Tuple[int, dict]], callback: Callable[[Optional[int], Optional[int]], None]):
        self.parent = parent
        self.mic_devices = mic_devices
        self.callback = callback
        
        # 测试状态
        self.is_testing = False
        self.test_thread = None
        
        # 创建窗口
        self.window = tk.Toplevel(parent)
        self.window.title("浏览器版设备校准")
        self.window.geometry("500x400")
        self.window.transient(parent)
        self.window.grab_set()
        
        # 居中显示
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (self.window.winfo_width() // 2)
        y = (self.window.winfo_screenheight() // 2) - (self.window.winfo_height() // 2)
        self.window.geometry(f"+{x}+{y}")
        
        self.create_widgets()
    
    def create_widgets(self):
        """创建UI组件"""
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="浏览器版设备校准", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 说明文字
        info_text = """
此校准工具专为浏览器音频采集版本设计：
• 只需要测试麦克风设备
• 浏览器音频通过WASAPI自动采集
• 请对着麦克风说话进行测试
        """
        info_label = ttk.Label(main_frame, text=info_text.strip(), justify=tk.LEFT)
        info_label.pack(pady=(0, 20))
        
        # 麦克风测试区域
        mic_frame = ttk.LabelFrame(main_frame, text="麦克风测试", padding="15")
        mic_frame.pack(fill=tk.X, pady=(0, 20))
        # 麦克风选择
        ttk.Label(mic_frame, text="选择麦克风设备:").pack(anchor=tk.W, pady=(0, 5))
        self.mic_var = tk.StringVar()
        self.mic_combo = ttk.Combobox(mic_frame, textvariable=self.mic_var, state="readonly", width=50)
        self.mic_combo.pack(fill=tk.X, pady=(0, 10))
        
        # 填充麦克风设备
        mic_options = []
        for device_id, device in self.mic_devices:
            mic_options.append(f"[{device_id}] {device['name']}")
        self.mic_combo['values'] = mic_options
        if mic_options:
            self.mic_combo.current(0)
        
        # 测试按钮
        button_frame = tk.Frame(mic_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.test_mic_btn = ttk.Button(button_frame, text="开始麦克风测试", command=self.toggle_mic_test)
        self.test_mic_btn.pack(side=tk.LEFT)
        
        # 音量指示器
        volume_frame = tk.Frame(mic_frame)
        volume_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(volume_frame, text="音量:").pack(side=tk.LEFT)
        self.volume_var = tk.DoubleVar()
        self.volume_bar = ttk.Progressbar(volume_frame, variable=self.volume_var, maximum=100)
        self.volume_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 10))
        
        self.volume_label = ttk.Label(volume_frame, text="0%")
        self.volume_label.pack(side=tk.LEFT)
        
        # 测试状态
        self.status_var = tk.StringVar(value="请选择设备并开始测试")
        status_label = ttk.Label(mic_frame, textvariable=self.status_var, foreground="blue")
        status_label.pack(pady=(10, 0))
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame, text="取消", command=self.cancel).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="确定", command=self.confirm).pack(side=tk.RIGHT)
    
    def toggle_mic_test(self):
        """切换麦克风测试状态"""
        if not self.is_testing:
            self.start_mic_test()
        else:
            self.stop_mic_test()
    
    def start_mic_test(self):
        """开始麦克风测试"""
        selection = self.mic_var.get()
        if not selection:
            messagebox.showerror("错误", "请选择麦克风设备")
            return
        
        try:
            device_id = int(selection.split(']')[0].split('[')[1])
        except:
            messagebox.showerror("错误", "无效的设备选择")
            return
        
        self.is_testing = True
        self.test_mic_btn.config(text="停止测试")
        self.status_var.set("正在测试麦克风，请对着麦克风说话...")
        
        # 启动测试线程
        self.test_thread = threading.Thread(target=self._mic_test_loop, args=(device_id,), daemon=True)
        self.test_thread.start()
    
    def stop_mic_test(self):
        """停止麦克风测试"""
        self.is_testing = False
        self.test_mic_btn.config(text="开始麦克风测试")
        self.status_var.set("测试已停止")
        self.volume_var.set(0)
        self.volume_label.config(text="0%")
    
    def _mic_test_loop(self, device_id: int):
        """麦克风测试循环"""
        try:
            def audio_callback(indata, frames, time, status):
                if status:
                    print(f"麦克风测试状态: {status}")
                
                if self.is_testing and len(indata) > 0:
                    # 计算音量
                    audio_data = indata[:, 0] if indata.shape[1] > 0 else indata.flatten()
                    volume = np.sqrt(np.mean(audio_data ** 2))
                    volume_percent = min(volume * 1000, 100)  # 放大并限制在100%
                    
                    # 更新UI
                    self.window.after(0, self._update_volume_display, volume_percent)
            
            # 启动音频流
            with sd.InputStream(
                device=device_id,
                channels=1,
                samplerate=44100,
                callback=audio_callback,
                blocksize=1024,
                dtype=np.float32
            ):
                while self.is_testing:
                    time.sleep(0.1)
                    
        except Exception as e:
            error_msg = str(e)
            self.window.after(0, lambda: self.status_var.set(f"测试失败: {error_msg}"))
            self.window.after(0, self.stop_mic_test)
    
    def _update_volume_display(self, volume_percent: float):
        """更新音量显示"""
        if self.is_testing:
            self.volume_var.set(volume_percent)
            self.volume_label.config(text=f"{volume_percent:.0f}%")
            
            # 根据音量更新状态
            if volume_percent > 10:
                self.status_var.set("✅ 麦克风工作正常！")
            else:
                self.status_var.set("🔇 请对着麦克风说话...")
    
    def confirm(self):
        """确认选择"""
        if self.is_testing:
            self.stop_mic_test()
        
        # 获取选中的麦克风设备
        mic_selection = self.mic_var.get()
        mic_id = None
        
        if mic_selection:
            try:
                mic_id = int(mic_selection.split(']')[0].split('[')[1])
            except:
                pass
        
        # 调用回调函数
        self.callback(mic_id, None)  # 浏览器版本不需要系统音频设备
        self.window.destroy()
    
    def cancel(self):
        """取消"""
        if self.is_testing:
            self.stop_mic_test()
        self.window.destroy()