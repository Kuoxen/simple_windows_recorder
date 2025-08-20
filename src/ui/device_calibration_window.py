import tkinter as tk
from tkinter import ttk, messagebox
import threading
from audio.device_calibrator import DeviceCalibrator

class DeviceCalibrationWindow:
    def __init__(self, parent, callback=None):
        self.parent = parent
        self.callback = callback
        self.calibrator = DeviceCalibrator()
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
        devices_frame = ttk.LabelFrame(main_frame, text="检测到的输入设备", padding="10")
        devices_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # 设备列表
        self.device_tree = ttk.Treeview(devices_frame, columns=("name", "volume"), show="tree headings", height=8)
        self.device_tree.heading("#0", text="ID")
        self.device_tree.heading("name", text="设备名称")
        self.device_tree.heading("volume", text="音量")
        self.device_tree.column("#0", width=50)
        self.device_tree.column("name", width=350)
        self.device_tree.column("volume", width=100)
        
        scrollbar = ttk.Scrollbar(devices_frame, orient=tk.VERTICAL, command=self.device_tree.yview)
        self.device_tree.configure(yscrollcommand=scrollbar.set)
        
        self.device_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 填充设备列表
        for device_id, device_info in self.calibrator.input_devices:
            self.device_tree.insert("", tk.END, iid=device_id, text=str(device_id), 
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
        
        self.skip_button = ttk.Button(button_frame, text="跳过校准", 
                                    command=self.skip_calibration,
                                    style='Calibration.TButton')
        self.skip_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.close_button = ttk.Button(button_frame, text="关闭", 
                                     command=self.close_window,
                                     style='Calibration.TButton')
        self.close_button.pack(side=tk.RIGHT)
        
    def update_device_volume(self, device_id, volume):
        """更新设备音量显示"""
        try:
            self.device_tree.set(device_id, "volume", f"{volume:.3f}")
            # 高亮活跃设备
            if volume > 0.01:
                self.device_tree.set(device_id, "name", f"🔊 {self.calibrator.get_device_name(device_id)}")
            else:
                self.device_tree.set(device_id, "name", self.calibrator.get_device_name(device_id))
        except:
            pass
    
    def start_calibration(self):
        """开始校准流程"""
        self.is_calibrating = True
        self.start_button.config(state='disabled')
        self.skip_button.config(state='disabled')
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
                    duration=5.0,
                    callback=lambda dev_id, vol: self.window.after(0, lambda: self.update_device_volume(dev_id, vol)) if self.is_calibrating else None
                )
                
                if not self.is_calibrating:
                    return
                
                # 系统音频测试阶段
                self.window.after(0, lambda: self.status_label.config(text="系统音频测试: 正在播放测试音频..."))
                self.window.after(0, lambda: self.safe_update_progress(60))
                
                # 重置显示
                for device_id, _ in self.calibrator.input_devices:
                    if not self.is_calibrating:
                        return
                    self.window.after(0, lambda did=device_id: self.safe_update_tree(did, "volume", "0.00"))
                    self.window.after(0, lambda did=device_id: self.safe_update_tree(did, "name", self.calibrator.get_device_name(did)))
                
                test_audio = self.calibrator.generate_test_audio(3.0)
                
                system_results = self.calibrator.test_system_audio_devices(
                    test_audio,
                    callback=lambda dev_id, vol: self.window.after(0, lambda: self.update_device_volume(dev_id, vol)) if self.is_calibrating else None
                )
                
                if not self.is_calibrating:
                    return
                
                # 完成阶段
                self.window.after(0, lambda: self.status_label.config(text="正在分析结果..."))
                self.window.after(0, lambda: self.safe_update_progress(95))
                
                # 选择最佳设备
                self.selected_mic = max(mic_results.items(), key=lambda x: x[1])[0] if mic_results else None
                self.selected_system = max(system_results.items(), key=lambda x: x[1])[0] if system_results else None
                
                self.window.after(0, lambda: self.safe_update_progress(100))
                self.window.after(0, lambda: self.status_label.config(text="校准完成！"))
                time.sleep(0.5)  # 让用户看到完成状态
                self.window.after(0, self.show_results)
                
            except Exception as e:
                if self.is_calibrating:
                    self.window.after(0, lambda: messagebox.showerror("错误", f"校准失败: {str(e)}"))
                self.window.after(0, self.reset_buttons)
        
        self.calibration_thread = threading.Thread(target=calibration_thread, daemon=True)
        self.calibration_thread.start()
        
        # 设置超时保护
        self.window.after(15000, self.check_calibration_timeout)  # 15秒超时
    
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
    
    def skip_calibration(self):
        """跳过校准"""
        if messagebox.askyesno("跳过校准", "确定要跳过设备校准吗？\n将使用默认设备选择逻辑。"):
            self.close_window()
    
    def cancel_calibration(self):
        """取消校准"""
        self.is_calibrating = False
        self.calibrator.is_testing = False
        self.status_label.config(text="校准已取消")
        self.reset_buttons()
    
    def safe_update_tree(self, device_id, column, value):
        """安全更新树形控件"""
        try:
            if self.device_tree.winfo_exists():
                self.device_tree.set(device_id, column, value)
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
        self.skip_button.config(state='normal')
        self.cancel_button.config(state='disabled')
        self.close_button.config(state='normal')
        self.status_label.config(text="准备开始校准...")
        try:
            self.progress.config(value=0)
        except:
            pass
    
    def check_calibration_timeout(self):
        """检查校准超时"""
        if self.is_calibrating:
            self.is_calibrating = False
            self.calibrator.is_testing = False
            messagebox.showwarning("超时", "校准超时（超过15秒），请检查设备连接后重试")
            self.reset_buttons()
    
    def close_window(self):
        """关闭窗口"""
        # 停止校准
        self.is_calibrating = False
        self.calibrator.is_testing = False
        
        # 等待线程结束
        if self.calibration_thread and self.calibration_thread.is_alive():
            self.calibration_thread.join(timeout=1.0)
        
        self.window.destroy()