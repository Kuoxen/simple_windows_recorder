import tkinter as tk
from tkinter import ttk, messagebox
import threading
from datetime import datetime
import os
import sys
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Settings
from audio.enhanced_device_manager import EnhancedDeviceManager
from audio.auto_recorder import AutoAudioRecorder
from storage.uploader import FileUploader

class AutoRecorderUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("智能呼叫中心录音系统 - 系统音频触发版")
        self.root.geometry("700x650")
        
        # 配置日志
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # 初始化组件
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config.yaml")
            self.settings = Settings(config_path)
            self.device_manager = EnhancedDeviceManager()
            self.auto_recorder = AutoAudioRecorder(self.settings)
            self.uploader = FileUploader(self.settings)
            
            # 设置回调
            self.auto_recorder.set_status_callback(self.on_recorder_status)
            
            self.setup_ui()
            self.load_devices()
            self.start_status_update()
        except Exception as e:
            print(f"初始化错误: {e}")
            self.setup_ui()
            self.log_message(f"初始化错误: {e}")
    
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 设备选择区域
        device_frame = ttk.LabelFrame(main_frame, text="设备选择", padding="10")
        device_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 麦克风选择
        mic_frame = tk.Frame(device_frame)
        mic_frame.pack(fill=tk.X, pady=2)
        ttk.Label(mic_frame, text="麦克风设备:").pack(side=tk.LEFT)
        self.mic_var = tk.StringVar()
        self.mic_combo = ttk.Combobox(mic_frame, textvariable=self.mic_var, width=50, state="readonly")
        self.mic_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
        # 系统音频选择
        system_frame = tk.Frame(device_frame)
        system_frame.pack(fill=tk.X, pady=2)
        ttk.Label(system_frame, text="系统音频:").pack(side=tk.LEFT)
        self.system_var = tk.StringVar()
        self.system_combo = ttk.Combobox(system_frame, textvariable=self.system_var, width=50, state="readonly")
        self.system_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
        # 刷新按钮
        ttk.Button(device_frame, text="刷新设备", command=self.refresh_devices).pack(pady=(5, 0))
        
        # 自动录制配置区域
        config_frame = ttk.LabelFrame(main_frame, text="自动录制配置", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 启用自动录制
        auto_frame = tk.Frame(config_frame)
        auto_frame.pack(fill=tk.X, pady=2)
        self.auto_enabled = tk.BooleanVar(value=self.settings.auto_recording.get('enabled', False))
        ttk.Checkbutton(auto_frame, text="启用自动录制", variable=self.auto_enabled, 
                       command=self.on_auto_enabled_changed).pack(side=tk.LEFT)
        
        # 触发说明
        trigger_info = tk.Frame(config_frame)
        trigger_info.pack(fill=tk.X, pady=(2, 5))
        info_label = ttk.Label(trigger_info, text="⚡ 触发机制：检测到系统音频有声音时自动开始录制", 
                           foreground="blue", font=("Arial", 9))
        info_label.pack(side=tk.LEFT)
        
        # 音量阈值
        threshold_frame = tk.Frame(config_frame)
        threshold_frame.pack(fill=tk.X, pady=2)
        ttk.Label(threshold_frame, text="音量阈值:").pack(side=tk.LEFT)
        self.threshold_var = tk.DoubleVar(value=self.settings.auto_recording.get('volume_threshold', 0.015))
        threshold_scale = ttk.Scale(threshold_frame, from_=0.005, to=0.1, variable=self.threshold_var, 
                                  orient=tk.HORIZONTAL, command=self.on_threshold_changed)
        threshold_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 10))
        self.threshold_label = ttk.Label(threshold_frame, text=f"{self.threshold_var.get():.3f}")
        self.threshold_label.pack(side=tk.RIGHT)
        
        # 静默时长
        silence_frame = tk.Frame(config_frame)
        silence_frame.pack(fill=tk.X, pady=2)
        ttk.Label(silence_frame, text="静默时长(秒):").pack(side=tk.LEFT)
        self.silence_var = tk.DoubleVar(value=self.settings.auto_recording.get('end_silence_duration', 12.0))
        silence_scale = ttk.Scale(silence_frame, from_=5.0, to=30.0, variable=self.silence_var,
                                orient=tk.HORIZONTAL, command=self.on_silence_changed)
        silence_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 10))
        self.silence_label = ttk.Label(silence_frame, text=f"{self.silence_var.get():.1f}s")
        self.silence_label.pack(side=tk.RIGHT)
        
        # 通话信息区域
        info_frame = ttk.LabelFrame(main_frame, text="通话信息", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 坐席手机号
        agent_frame = tk.Frame(info_frame)
        agent_frame.pack(fill=tk.X, pady=2)
        ttk.Label(agent_frame, text="坐席手机号:").pack(side=tk.LEFT)
        self.agent_phone = tk.StringVar()
        ttk.Entry(agent_frame, textvariable=self.agent_phone, width=20).pack(side=tk.RIGHT, padx=(10, 0))
        
        # 客户姓名
        customer_frame = tk.Frame(info_frame)
        customer_frame.pack(fill=tk.X, pady=2)
        ttk.Label(customer_frame, text="客户姓名:").pack(side=tk.LEFT)
        self.customer_name = tk.StringVar()
        ttk.Entry(customer_frame, textvariable=self.customer_name, width=20).pack(side=tk.RIGHT, padx=(10, 0))
        
        # 客户ID
        id_frame = tk.Frame(info_frame)
        id_frame.pack(fill=tk.X, pady=2)
        ttk.Label(id_frame, text="客户ID:").pack(side=tk.LEFT)
        self.customer_id = tk.StringVar()
        ttk.Entry(id_frame, textvariable=self.customer_id, width=20).pack(side=tk.RIGHT, padx=(10, 0))
        
        # 控制区域
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.monitor_btn = ttk.Button(control_frame, text="开始监听", command=self.toggle_monitoring)
        self.monitor_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 状态显示
        status_frame = tk.Frame(control_frame)
        status_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, foreground="green")
        self.status_label.pack(side=tk.LEFT)
        
        # 实时状态区域
        realtime_frame = ttk.LabelFrame(main_frame, text="实时状态", padding="10")
        realtime_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 状态指示器
        indicators_frame = tk.Frame(realtime_frame)
        indicators_frame.pack(fill=tk.X)
        
        # 麦克风活动指示器
        mic_indicator_frame = tk.Frame(indicators_frame)
        mic_indicator_frame.pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(mic_indicator_frame, text="麦克风:").pack(side=tk.LEFT)
        self.mic_indicator = tk.Label(mic_indicator_frame, text="●", fg="gray", font=("Arial", 16))
        self.mic_indicator.pack(side=tk.LEFT, padx=(5, 0))
        
        # 系统音频活动指示器
        system_indicator_frame = tk.Frame(indicators_frame)
        system_indicator_frame.pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(system_indicator_frame, text="系统音频:").pack(side=tk.LEFT)
        self.system_indicator = tk.Label(system_indicator_frame, text="●", fg="gray", font=("Arial", 16))
        self.system_indicator.pack(side=tk.LEFT, padx=(5, 0))
        
        # 录制状态指示器
        record_indicator_frame = tk.Frame(indicators_frame)
        record_indicator_frame.pack(side=tk.LEFT)
        ttk.Label(record_indicator_frame, text="录制:").pack(side=tk.LEFT)
        self.record_indicator = tk.Label(record_indicator_frame, text="●", fg="gray", font=("Arial", 16))
        self.record_indicator.pack(side=tk.LEFT, padx=(5, 0))
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="系统日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        text_frame = tk.Frame(log_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(text_frame, height=12, width=70)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def load_devices(self):
        """加载设备列表"""
        try:
            recommendations = self.device_manager.get_recommended_devices()
            
            # 加载麦克风设备
            physical_mics = self.device_manager.get_physical_microphones()
            mic_options = []
            for device_id, device in physical_mics:
                available = self.device_manager.test_device_availability(device_id)
                status = "✅" if available else "❌"
                mic_options.append(f"{status} [{device_id}] {device['name']}")
            
            self.mic_combo['values'] = mic_options
            
            # 加载系统音频设备
            loopback_devices = self.device_manager.get_loopback_devices()
            system_options = []
            for device_id, device in loopback_devices:
                available = self.device_manager.test_device_availability(device_id)
                status = "✅" if available else "❌"
                system_options.append(f"{status} [{device_id}] {device['name']}")
            
            self.system_combo['values'] = system_options
            
            # 自动选择推荐设备
            if recommendations['microphone'] is not None:
                for i, option in enumerate(mic_options):
                    if f"[{recommendations['microphone']}]" in option:
                        self.mic_combo.current(i)
                        break
            
            if recommendations['system_audio'] is not None:
                for i, option in enumerate(system_options):
                    if f"[{recommendations['system_audio']}]" in option:
                        self.system_combo.current(i)
                        break
            
            self.log_message(f"设备加载完成 - 麦克风:{len(mic_options)}个, 系统音频:{len(system_options)}个")
            
        except Exception as e:
            self.log_message(f"设备加载失败: {e}")
    
    def refresh_devices(self):
        """刷新设备列表"""
        self.log_message("正在刷新设备列表...")
        self.device_manager = EnhancedDeviceManager()
        self.load_devices()
    
    def get_selected_device_id(self, combo_value):
        """从组合框值中提取设备ID"""
        if not combo_value or "❌" in combo_value:
            return None
        try:
            return int(combo_value.split(']')[0].split('[')[1])
        except:
            return None
    
    def toggle_monitoring(self):
        """切换监听状态"""
        if not self.auto_recorder.is_monitoring:
            self.start_monitoring()
        else:
            self.stop_monitoring()
    
    def start_monitoring(self):
        """开始监听"""
        if not self.auto_enabled.get():
            messagebox.showwarning("警告", "请先启用自动录制功能")
            return
        
        mic_id = self.get_selected_device_id(self.mic_var.get())
        system_id = self.get_selected_device_id(self.system_var.get())
        
        if mic_id is None:
            messagebox.showerror("错误", "请选择可用的麦克风设备")
            return
        
        if system_id is None:
            messagebox.showerror("错误", "请选择可用的系统音频设备")
            return
        
        # 设置设备和通话信息
        self.auto_recorder.set_devices(mic_id, system_id)
        self.auto_recorder.set_call_info(
            self.agent_phone.get(),
            self.customer_name.get(),
            self.customer_id.get()
        )
        
        def monitor_thread():
            if self.auto_recorder.start_monitoring():
                self.root.after(0, self.update_monitoring_ui, True)
            else:
                self.root.after(0, messagebox.showerror, "错误", "无法开始监听")
        
        threading.Thread(target=monitor_thread, daemon=True).start()
    
    def stop_monitoring(self):
        """停止监听"""
        def stop_thread():
            self.auto_recorder.stop_monitoring()
            self.root.after(0, self.update_monitoring_ui, False)
        
        threading.Thread(target=stop_thread, daemon=True).start()
    
    def update_monitoring_ui(self, monitoring):
        """更新监听UI状态"""
        if monitoring:
            self.monitor_btn.config(text="停止监听")
            self.status_var.set("监听中...")
            self.status_label.config(foreground="blue")
        else:
            self.monitor_btn.config(text="开始监听")
            self.status_var.set("就绪")
            self.status_label.config(foreground="green")
    
    def start_status_update(self):
        """开始状态更新循环"""
        self.update_status_indicators()
        self.root.after(500, self.start_status_update)  # 每500ms更新一次
    
    def update_status_indicators(self):
        """更新状态指示器"""
        try:
            status = self.auto_recorder.get_status()
            
            # 更新麦克风指示器
            if status.get('mic_active', False):
                self.mic_indicator.config(fg="green")
            else:
                self.mic_indicator.config(fg="gray")
            
            # 更新系统音频指示器
            if status.get('system_active', False):
                self.system_indicator.config(fg="green")
            else:
                self.system_indicator.config(fg="gray")
            
            # 更新录制指示器
            if status.get('state') == 'recording':
                self.record_indicator.config(fg="red")
            elif status.get('monitoring', False):
                self.record_indicator.config(fg="orange")
            else:
                self.record_indicator.config(fg="gray")
            
        except Exception as e:
            pass  # 忽略状态更新错误
    
    def on_auto_enabled_changed(self):
        """自动录制启用状态改变"""
        enabled = self.auto_enabled.get()
        self.settings.update_auto_recording('enabled', enabled)
        self.log_message(f"自动录制已{'启用' if enabled else '禁用'}")
    
    def on_threshold_changed(self, value):
        """音量阈值改变"""
        threshold = float(value)
        self.threshold_label.config(text=f"{threshold:.3f}")
        self.auto_recorder.update_config('volume_threshold', threshold)
    
    def on_silence_changed(self, value):
        """静默时长改变"""
        silence = float(value)
        self.silence_label.config(text=f"{silence:.1f}s")
        self.auto_recorder.update_config('end_silence_duration', silence)
    
    def on_recorder_status(self, message):
        """录制器状态回调"""
        self.root.after(0, self.log_message, message)
    
    def log_message(self, message):
        """记录日志消息"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)
        except:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = AutoRecorderUI()
    app.run()