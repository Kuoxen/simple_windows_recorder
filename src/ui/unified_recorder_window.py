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
from audio.enhanced_recorder import EnhancedAudioRecorder
from audio.auto_recorder import AutoAudioRecorder
from storage.uploader import FileUploader
from ui.device_calibration_window import DeviceCalibrationWindow

class UnifiedRecorderUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("岩硅智能音频采集器")
        self.root.geometry("700x700")
        
        # 配置日志
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # 录制模式
        self.is_auto_mode = tk.BooleanVar(value=False)
        self.is_recording = False
        self.is_monitoring = False
        
        # 初始化组件
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config.yaml")
            self.settings = Settings(config_path)
            self.device_manager = EnhancedDeviceManager()
            self.manual_recorder = EnhancedAudioRecorder(self.settings)
            self.auto_recorder = AutoAudioRecorder(self.settings)
            self.uploader = FileUploader(self.settings)
            
            # 设置回调
            self.manual_recorder.set_status_callback(self.on_recorder_status)
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
        
        # 共享的设备选择区域
        self.setup_device_selection(main_frame)
        
        # 共享的通话信息区域
        self.setup_call_info(main_frame)
        
        # 录制模式Tab区域
        mode_frame = ttk.LabelFrame(main_frame, text="录制模式", padding="10")
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 创建Tab控件
        self.notebook = ttk.Notebook(mode_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 手动录制Tab
        self.manual_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.manual_frame, text="手动录制")
        
        # 自动录制Tab
        self.auto_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.auto_frame, text="自动录制")
        
        # 设置Tab切换回调
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # 设置手动录制界面
        self.setup_manual_ui()
        
        # 设置自动录制界面
        self.setup_auto_ui()
        

        

        
        # 日志区域（共享）
        log_frame = ttk.LabelFrame(main_frame, text="系统日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        text_frame = tk.Frame(log_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(text_frame, height=15, width=70)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_device_selection(self, parent):
        """设置共享的设备选择区域"""
        device_frame = ttk.LabelFrame(parent, text="设备选择", padding="10")
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
        
        # 按钮框架
        button_frame = tk.Frame(device_frame)
        button_frame.pack(pady=(5, 0))
        
        ttk.Button(button_frame, text="设备校准", command=self.open_calibration_window).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="刷新设备", command=self.refresh_devices).pack(side=tk.LEFT)
    
    def setup_call_info(self, parent):
        """设置共享的通话信息区域"""
        info_frame = ttk.LabelFrame(parent, text="通话信息", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 坐席手机号
        agent_frame = tk.Frame(info_frame)
        agent_frame.pack(fill=tk.X, pady=2)
        ttk.Label(agent_frame, text="坐席手机号:").pack(side=tk.LEFT)
        self.agent_phone = tk.StringVar()
        ttk.Entry(agent_frame, textvariable=self.agent_phone, width=20).pack(side=tk.RIGHT, padx=(10, 0))
        
        # 初始化空的客户信息变量（保持兼容性）
        self.customer_name = tk.StringVar()
        self.customer_id = tk.StringVar()
    
    def setup_manual_ui(self):
        """设置手动录制界面"""
        # 控制区域
        control_frame = ttk.Frame(self.manual_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        self.manual_btn = ttk.Button(control_frame, text="开始录音", command=self.toggle_manual_recording)
        self.manual_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 状态显示
        self.manual_status_var = tk.StringVar(value="就绪")
        self.manual_status_label = ttk.Label(control_frame, textvariable=self.manual_status_var, foreground="green")
        self.manual_status_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 时长显示
        self.duration_var = tk.StringVar(value="00:00")
        ttk.Label(control_frame, textvariable=self.duration_var).pack(side=tk.LEFT)
    
    def setup_auto_ui(self):
        """设置自动录制界面"""
        # 自动录制配置区域
        config_frame = ttk.LabelFrame(self.auto_frame, text="自动录制配置", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
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
        
        # 实时状态指示器
        indicators_frame = tk.Frame(config_frame)
        indicators_frame.pack(fill=tk.X, pady=(10, 0))
        
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
        
        # 控制区域
        control_frame = ttk.Frame(self.auto_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        self.auto_btn = ttk.Button(control_frame, text="开始监听", command=self.toggle_auto_recording)
        self.auto_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 状态显示
        self.auto_status_var = tk.StringVar(value="就绪")
        self.auto_status_label = ttk.Label(control_frame, textvariable=self.auto_status_var, foreground="green")
        self.auto_status_label.pack(side=tk.LEFT)
    
    def on_tab_changed(self, event):
        """处理Tab切换事件"""
        selected_tab = self.notebook.index(self.notebook.select())
        if selected_tab == 0:
            self.log_message("切换到手动录制模式")
        else:
            self.log_message("切换到自动录制模式")
    
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
            
            # 加载系统音频设备
            loopback_devices = self.device_manager.get_loopback_devices()
            system_options = []
            for device_id, device in loopback_devices:
                available = self.device_manager.test_device_availability(device_id)
                status = "✅" if available else "❌"
                system_options.append(f"{status} [{device_id}] {device['name']}")
            
            # 更新共享的设备列表
            self.mic_combo['values'] = mic_options
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
    
    def open_calibration_window(self):
        """打开设备校准窗口"""
        def on_calibration_complete(mic_id, system_id):
            """校准完成回调"""
            if mic_id is not None:
                # 在麦克风列表中选择校准结果
                for i, option in enumerate(self.mic_combo['values']):
                    if f"[{mic_id}]" in option:
                        self.mic_combo.current(i)
                        break
                self.log_message(f"已选择麦克风设备: {mic_id}")
            
            if system_id is not None:
                # 在系统音频列表中选择校准结果
                for i, option in enumerate(self.system_combo['values']):
                    if f"[{system_id}]" in option:
                        self.system_combo.current(i)
                        break
                self.log_message(f"已选择系统音频设备: {system_id}")
        
        try:
            DeviceCalibrationWindow(self.root, on_calibration_complete)
        except Exception as e:
            messagebox.showerror("错误", f"无法打开校准窗口: {e}")
    
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
    
    def toggle_manual_recording(self):
        """切换手动录制状态"""
        if not self.is_recording:
            self.start_manual_recording()
        else:
            self.stop_manual_recording()
    
    def toggle_auto_recording(self):
        """切换自动录制状态"""
        if not self.is_monitoring:
            self.start_auto_monitoring()
        else:
            self.stop_auto_monitoring()
    
    def start_manual_recording(self):
        """开始手动录制"""
        # 校验坐席手机号
        if not self.agent_phone.get().strip():
            messagebox.showerror("错误", "请填写坐席手机号")
            return
        
        mic_id = self.get_selected_device_id(self.mic_var.get())
        system_id = self.get_selected_device_id(self.system_var.get())
        
        if mic_id is None:
            messagebox.showerror("错误", "请选择可用的麦克风设备")
            return
        
        if system_id is None:
            if not messagebox.askyesno("确认", "未选择系统音频设备，将只录制麦克风。是否继续？"):
                return
        
        def record_thread():
            if self.manual_recorder.start_recording(mic_id, system_id):
                self.is_recording = True
                self.root.after(0, self.update_manual_ui, True)
                self.root.after(0, self.start_duration_timer)
            else:
                self.root.after(0, messagebox.showerror, "错误", "无法开始录音")
        
        threading.Thread(target=record_thread, daemon=True).start()
    
    def stop_manual_recording(self):
        """停止手动录制"""
        def stop_thread():
            result = self.manual_recorder.stop_recording()
            self.is_recording = False
            self.root.after(0, self.update_manual_ui, False)
            
            if result:
                self.root.after(0, self.process_recording_result, result)
        
        threading.Thread(target=stop_thread, daemon=True).start()
    
    def start_auto_monitoring(self):
        """开始自动监听"""
        # 校验坐席手机号
        if not self.agent_phone.get().strip():
            messagebox.showerror("错误", "请填写坐席手机号")
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
                self.is_monitoring = True
                self.root.after(0, self.update_auto_ui, True)
            else:
                self.root.after(0, messagebox.showerror, "错误", "无法开始监听")
        
        threading.Thread(target=monitor_thread, daemon=True).start()
    
    def stop_auto_monitoring(self):
        """停止自动监听"""
        def stop_thread():
            self.auto_recorder.stop_monitoring()
            self.is_monitoring = False
            self.root.after(0, self.update_auto_ui, False)
        
        threading.Thread(target=stop_thread, daemon=True).start()
    
    def update_manual_ui(self, recording):
        """更新手动录制UI"""
        if recording:
            self.manual_btn.config(text="停止录音")
            self.manual_status_var.set("录音中...")
            self.manual_status_label.config(foreground="red")
        else:
            self.manual_btn.config(text="开始录音")
            self.manual_status_var.set("就绪")
            self.manual_status_label.config(foreground="green")
            self.duration_var.set("00:00")
    
    def update_auto_ui(self, monitoring):
        """更新自动录制UI"""
        if monitoring:
            self.auto_btn.config(text="停止监听")
            self.auto_status_var.set("监听中...")
            self.auto_status_label.config(foreground="blue")
        else:
            self.auto_btn.config(text="开始监听")
            self.auto_status_var.set("就绪")
            self.auto_status_label.config(foreground="green")
    
    def start_status_update(self):
        """开始状态更新循环"""
        self.update_status_indicators()
        self.root.after(500, self.start_status_update)
    
    def update_status_indicators(self):
        """更新状态指示器"""
        try:
            # 只在自动录制Tab且正在监听时更新指示器
            current_tab = self.notebook.index(self.notebook.select())
            if current_tab == 1 and self.is_monitoring:  # 自动录制Tab
                status = self.auto_recorder.get_status()
                
                # 更新指示器
                self.mic_indicator.config(fg="green" if status.get('mic_active', False) else "gray")
                self.system_indicator.config(fg="green" if status.get('system_active', False) else "gray")
                
                if status.get('state') == 'recording':
                    self.record_indicator.config(fg="red")
                elif status.get('monitoring', False):
                    self.record_indicator.config(fg="orange")
                else:
                    self.record_indicator.config(fg="gray")
            else:
                # 重置指示器
                self.mic_indicator.config(fg="gray")
                self.system_indicator.config(fg="gray")
                self.record_indicator.config(fg="gray")
        except:
            pass
    
    def start_duration_timer(self):
        """开始时长计时器"""
        if self.is_recording:
            status = self.manual_recorder.get_recording_status()
            if status['recording']:
                duration = int(status['duration'])
                minutes = duration // 60
                seconds = duration % 60
                self.duration_var.set(f"{minutes:02d}:{seconds:02d}")
            
            self.root.after(1000, self.start_duration_timer)
    
    def process_recording_result(self, result):
        """处理录制结果"""
        # 生成文件名并重命名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_parts = [timestamp]
        
        # 使用手动录制Tab的变量
        if self.agent_phone.get():
            filename_parts.extend(['Agent', self.agent_phone.get()])
        if self.customer_name.get():
            filename_parts.extend(['Customer', self.customer_name.get()])
        if self.customer_id.get():
            filename_parts.extend(['ID', self.customer_id.get()])
        
        base_filename = '_'.join(filename_parts)
        
        if result['mic_success'] and result['mic_file']:
            new_mic_file = os.path.join(os.path.dirname(result['mic_file']), f"mic_{base_filename}.wav")
            os.rename(result['mic_file'], new_mic_file)
            self.log_message(f"✅ 麦克风文件: {os.path.basename(new_mic_file)}")
        
        if result['speaker_success'] and result['speaker_file']:
            new_system_file = os.path.join(os.path.dirname(result['speaker_file']), f"system_{base_filename}.wav")
            os.rename(result['speaker_file'], new_system_file)
            self.log_message(f"✅ 系统音频文件: {os.path.basename(new_system_file)}")
        
        self.log_message(f"录音完成! 时长: {result['duration']:.2f} 秒")
        
        # 自动上传文件
        if (result['mic_success'] or result['speaker_success']) and self.settings.upload.get('enabled', False):
            call_info = {
                'agent_phone': self.agent_phone.get(),
                'customer_name': self.customer_name.get(),
                'customer_id': self.customer_id.get()
            }
            self.log_message("开始上传文件...")
            
            # 使用重命名后的文件路径
            mic_file = new_mic_file if result['mic_success'] and result['mic_file'] else None
            system_file = new_system_file if result['speaker_success'] and result['speaker_file'] else None
            
            self.uploader.upload_files(mic_file, system_file, call_info, self.upload_callback)
    
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
    
    def upload_callback(self, success, message):
        """上传回调函数"""
        self.root.after(0, self.log_message, message)
    
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
    app = UnifiedRecorderUI()
    app.run()