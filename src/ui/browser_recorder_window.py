import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
from typing import Optional

from ..audio.browser_audio_recorder import BrowserAudioRecorder
from ..audio.device_manager import DeviceManager

class BrowserRecorderWindow:
    """浏览器音频录制器UI"""
    
    def __init__(self, settings):
        self.settings = settings
        self.recorder = BrowserAudioRecorder(settings)
        self.device_manager = DeviceManager()
        self.logger = logging.getLogger(__name__)
        
        # 设置录制器回调
        self.recorder.set_status_callback(self._on_status_update)
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("浏览器音频录制器")
        self.root.geometry("600x500")
        
        # 状态变量
        self.status_text = tk.StringVar(value="就绪")
        
        self._create_widgets()
        self._update_devices()
    
    def _create_widgets(self):
        """创建UI组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 设备选择
        device_frame = ttk.LabelFrame(main_frame, text="设备选择", padding="10")
        device_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(device_frame, text="麦克风设备:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.mic_combo = ttk.Combobox(device_frame, width=50, state="readonly")
        self.mic_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        ttk.Button(device_frame, text="刷新设备", command=self._update_devices).grid(
            row=0, column=2, padx=(10, 0), pady=2
        )
        
        # 浏览器状态
        browser_frame = ttk.LabelFrame(main_frame, text="浏览器状态", padding="10")
        browser_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.browser_status_label = ttk.Label(browser_frame, text="检测中...")
        self.browser_status_label.grid(row=0, column=0, sticky=tk.W)
        
        # 通话信息
        info_frame = ttk.LabelFrame(main_frame, text="通话信息", padding="10")
        info_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(info_frame, text="坐席手机号:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.agent_phone_entry = ttk.Entry(info_frame, width=20)
        self.agent_phone_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        ttk.Label(info_frame, text="客户姓名:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.customer_name_entry = ttk.Entry(info_frame, width=20)
        self.customer_name_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        ttk.Label(info_frame, text="客户ID:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.customer_id_entry = ttk.Entry(info_frame, width=20)
        self.customer_id_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=2)
        
        # 控制按钮
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=3, column=0, columnspan=2, pady=(0, 10))
        
        self.start_button = ttk.Button(
            control_frame, text="开始监听", command=self._start_monitoring
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(
            control_frame, text="停止监听", command=self._stop_monitoring, state="disabled"
        )
        self.stop_button.pack(side=tk.LEFT)
        
        # 状态显示
        status_frame = ttk.LabelFrame(main_frame, text="状态", padding="10")
        status_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, textvariable=self.status_text)
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        # 日志显示
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="10")
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.log_text = tk.Text(log_frame, height=10, width=70)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        device_frame.columnconfigure(1, weight=1)
        info_frame.columnconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 启动浏览器状态更新
        self._update_browser_status()
    
    def _update_devices(self):
        """更新设备列表"""
        try:
            input_devices = self.device_manager.get_input_devices()
            
            # 更新麦克风设备
            mic_names = [f"{i}: {dev['name']}" for i, dev in enumerate(input_devices)]
            self.mic_combo['values'] = mic_names
            
            if mic_names:
                self.mic_combo.current(0)
            
            self._log("设备列表已更新")
            
        except Exception as e:
            self._log(f"更新设备列表失败: {e}")
    
    def _update_browser_status(self):
        """更新浏览器状态"""
        try:
            sessions = self.recorder.wasapi_recorder.get_browser_sessions()
            if sessions:
                browser_names = [s['name'] for s in sessions]
                status_text = f"检测到浏览器: {', '.join(set(browser_names))}"
            else:
                status_text = "未检测到浏览器进程"
            
            self.browser_status_label.config(text=status_text)
            
        except Exception as e:
            self.browser_status_label.config(text=f"检测失败: {e}")
        
        # 每5秒更新一次
        self.root.after(5000, self._update_browser_status)
    
    def _start_monitoring(self):
        """开始监听"""
        try:
            # 获取选中的设备
            mic_selection = self.mic_combo.get()
            if not mic_selection:
                messagebox.showerror("错误", "请选择麦克风设备")
                return
            
            mic_device_id = int(mic_selection.split(':')[0])
            
            # 设置设备
            self.recorder.set_devices(mic_device_id)
            
            # 设置通话信息
            self.recorder.set_call_info(
                agent_phone=self.agent_phone_entry.get().strip(),
                customer_name=self.customer_name_entry.get().strip(),
                customer_id=self.customer_id_entry.get().strip()
            )
            
            # 在后台线程启动监听
            def start_in_thread():
                success = self.recorder.start_monitoring()
                if success:
                    self.root.after(0, self._on_monitoring_started)
                else:
                    self.root.after(0, lambda: self._log("启动监听失败"))
            
            threading.Thread(target=start_in_thread, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("错误", f"启动监听失败: {e}")
    
    def _stop_monitoring(self):
        """停止监听"""
        try:
            def stop_in_thread():
                self.recorder.stop_monitoring()
                self.root.after(0, self._on_monitoring_stopped)
            
            threading.Thread(target=stop_in_thread, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("错误", f"停止监听失败: {e}")
    
    def _on_monitoring_started(self):
        """监听开始后的UI更新"""
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_text.set("监听中...")
    
    def _on_monitoring_stopped(self):
        """监听停止后的UI更新"""
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_text.set("已停止")
    
    def _on_status_update(self, message: str):
        """状态更新回调"""
        # 在主线程中更新UI
        self.root.after(0, lambda: self._log(message))
        self.root.after(0, lambda: self.status_text.set(message))
    
    def _log(self, message: str):
        """添加日志"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        
        # 限制日志行数
        lines = int(self.log_text.index('end-1c').split('.')[0])
        if lines > 100:
            self.log_text.delete('1.0', '10.0')
    
    def run(self):
        """运行应用"""
        try:
            self.root.mainloop()
        finally:
            # 确保停止录制器
            if self.recorder.is_monitoring:
                self.recorder.stop_monitoring()