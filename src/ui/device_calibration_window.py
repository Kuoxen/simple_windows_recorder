import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from audio.device_calibrator import DeviceCalibrator

class DeviceCalibrationWindow:
    def __init__(self, parent, mic_devices, system_devices, callback=None):
        self.parent = parent
        self.callback = callback
        self.calibrator = DeviceCalibrator(mic_devices, system_devices)
        self.selected_mic = None
        self.selected_system = None
        self.calibration_thread = None
        self.is_calibrating = False
        
        self.setup_ui()
        
    def setup_ui(self):
        self.window = tk.Toplevel(self.parent)
        self.window.title("设备校准向导")
        self.window.geometry("600x550")
        self.window.resizable(True, True)
        self.window.minsize(600, 550)
        self.window.grab_set()
        
        # 主框架
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.grid_rowconfigure(2, weight=1)  # 设备列表可扩展
        
        # 标题
        title_label = ttk.Label(main_frame, text="设备校准向导", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 说明
        info_text = """通过实际测试自动选择最佳录音设备：
1. 麦克风测试：请对着麦克风说话
2. 系统音频测试：软件将播放测试音频"""
        
        info_label = ttk.Label(main_frame, text=info_text, justify=tk.LEFT)
        info_label.pack(pady=(0, 20))
        
        # 设备列表框架
        devices_frame = ttk.LabelFrame(main_frame, text="设备列表", padding="10")
        devices_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # 创建两列布局
        devices_container = ttk.Frame(devices_frame)
        devices_container.pack(fill=tk.BOTH, expand=True)
        
        # 麦克风设备列表
        mic_frame = ttk.LabelFrame(devices_container, text="麦克风设备", padding="5")
        mic_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.mic_tree = ttk.Treeview(mic_frame, columns=("name",), show="tree headings", height=6)
        self.mic_tree.heading("#0", text="ID")
        self.mic_tree.heading("name", text="设备名称")
        self.mic_tree.column("#0", width=30)
        self.mic_tree.column("name", width=260)
        self.mic_tree.pack(fill=tk.BOTH, expand=True)
        
        # 系统音频设备列表
        system_frame = ttk.LabelFrame(devices_container, text="系统音频设备", padding="5")
        system_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.system_tree = ttk.Treeview(system_frame, columns=("name", "volume"), show="tree headings", height=6)
        self.system_tree.heading("#0", text="ID")
        self.system_tree.heading("name", text="设备名称")
        self.system_tree.heading("volume", text="音量")
        self.system_tree.column("#0", width=30)
        self.system_tree.column("name", width=200)
        self.system_tree.column("volume", width=60)
        self.system_tree.pack(fill=tk.BOTH, expand=True)
        
        # 填充麦克风设备列表
        for device_id, device_info in self.calibrator.mic_devices:
            self.mic_tree.insert("", tk.END, iid=device_id, text=str(device_id), 
                               values=(device_info['name'],))
        
        # 填充系统音频设备列表
        for device_id, device_info in self.calibrator.system_devices:
            self.system_tree.insert("", tk.END, iid=device_id, text=str(device_id), 
                                  values=(device_info['name'], "0.00"))
        
        # 进度和状态
        self.status_label = ttk.Label(main_frame, text="准备开始校准...")
        self.status_label.pack(pady=(0, 10))
        
        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(0, 20))
        
        # 按钮框架 - 使用grid布局确保按钮有足够高度
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 设置按钮样式，确保有足够高度
        button_style = ttk.Style()
        button_style.configure('Calibration.TButton', padding=(10, 8))
        
        self.start_button = ttk.Button(button_frame, text="开始校准", 
                                     command=self.start_calibration, 
                                     style='Calibration.TButton')
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.cancel_button = ttk.Button(button_frame, text="取消校准", 
                                      command=self.cancel_calibration,
                                      style='Calibration.TButton')
        self.cancel_button.pack(side=tk.LEFT, padx=(0, 10))
        self.cancel_button.config(state='disabled')
        

        
        self.close_button = ttk.Button(button_frame, text="关闭", 
                                     command=self.close_window,
                                     style='Calibration.TButton')
        self.close_button.pack(side=tk.RIGHT)
        
    def update_device_volume(self, device_id, volume):
        """更新设备音量显示（只用于系统音频设备）"""
        try:
            # 只更新系统音频设备的音量显示
            self.system_tree.set(device_id, "volume", f"{volume:.3f}")
            # 高亮活跃设备
            if volume > 0.01:
                self.system_tree.set(device_id, "name", f"🔊 {self.calibrator.get_device_name(device_id)}")
            else:
                self.system_tree.set(device_id, "name", self.calibrator.get_device_name(device_id))
        except:
            pass
    
    def start_calibration(self):
        """开始校准流程"""
        self.is_calibrating = True
        self.start_button.config(state='disabled')
        self.cancel_button.config(state='normal')
        self.close_button.config(state='disabled')
        
        def calibration_thread():
            try:
                # 检查是否被取消
                if not self.is_calibrating:
                    return
                
                # 麦克风测试阶段
                self.window.after(0, lambda: self.status_label.config(text="麦克风测试: 请对着麦克风说话..."))
                self.window.after(0, lambda: self.safe_update_progress(10))
                
                mic_results = self.calibrator.test_microphone_devices(
                    duration=3.0,  # 改为3秒
                    callback=None  # 去掉UI刷新
                )
                
                if not self.is_calibrating:
                    return
                
                # 系统音频测试阶段
                self.window.after(0, lambda: self.status_label.config(text="系统音频测试: 正在播放测试音频..."))
                self.window.after(0, lambda: self.safe_update_progress(60))
                

                
                test_audio = self.calibrator.generate_test_audio(3.0)
                
                system_results = self.calibrator.test_system_audio_devices(
                    test_audio,
                    callback=lambda dev_id, vol: self.window.after(0, lambda: self.update_device_volume(dev_id, vol)) if self.is_calibrating else None
                )
                
                if not self.is_calibrating:
                    return
                
                # 选择最佳设备
                self.selected_mic = max(mic_results.items(), key=lambda x: x[1])[0] if mic_results else None
                self.selected_system = max(system_results.items(), key=lambda x: x[1])[0] if system_results else None
                
                self.window.after(0, lambda: self.safe_update_progress(100))
                self.window.after(0, lambda: self.status_label.config(text="校准完成！"))
                self.window.after(0, self.show_results)
                
            except Exception as e:
                if self.is_calibrating:
                    self.window.after(0, lambda: messagebox.showerror("错误", f"校准失败: {str(e)}"))
                self.window.after(0, self.reset_buttons)
        
        self.calibration_thread = threading.Thread(target=calibration_thread, daemon=True)
        self.calibration_thread.start()
    
    def show_results(self):
        """显示校准结果"""
        mic_name = self.calibrator.get_device_name(self.selected_mic) if self.selected_mic is not None else "未检测到"
        system_name = self.calibrator.get_device_name(self.selected_system) if self.selected_system is not None else "未检测到"
        
        result_text = f"""校准完成！

推荐设备：
• 麦克风: {mic_name}
• 系统音频: {system_name}

是否使用推荐设备？"""
        
        if messagebox.askyesno("校准结果", result_text):
            self.apply_results()
        else:
            self.reset_buttons()
    
    def apply_results(self):
        """应用校准结果"""
        if self.callback:
            self.callback(self.selected_mic, self.selected_system)
        self.close_window()
    

    
    def cancel_calibration(self):
        """取消校准"""
        self.is_calibrating = False
        self.calibrator.is_testing = False
        self.status_label.config(text="校准已取消")
        self.reset_buttons()
    
    def safe_update_tree(self, device_id, column, value):
        """安全更新树形控件（只用于系统音频设备重置）"""
        try:
            # 只重置系统音频设备的显示
            if self.system_tree.winfo_exists():
                self.system_tree.set(device_id, column, value)
        except:
            pass
    
    def safe_update_progress(self, value):
        """安全更新进度条"""
        try:
            if self.progress.winfo_exists():
                self.progress.config(value=value)
        except:
            pass
    
    def reset_buttons(self):
        """重置按钮状态"""
        self.is_calibrating = False
        self.start_button.config(state='normal')
        self.cancel_button.config(state='disabled')
        self.close_button.config(state='normal')
        self.status_label.config(text="准备开始校准...")
        try:
            self.progress.config(value=0)
        except:
            pass
    

    
    def close_window(self):
        """关闭窗口"""
        # 停止校准
        self.is_calibrating = False
        self.calibrator.is_testing = False
        
        # 等待线程结束
        if self.calibration_thread and self.calibration_thread.is_alive():
            self.calibration_thread.join(timeout=1.0)
        
        self.window.destroy()