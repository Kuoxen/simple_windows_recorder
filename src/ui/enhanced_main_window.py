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
from storage.uploader import FileUploader

class EnhancedRecorderUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("岩硅智能音频采集器")
        self.root.geometry("600x500")
        
        # 配置日志
        logging.basicConfig(level=logging.INFO)
        
        # 初始化组件
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config.yaml")
            self.settings = Settings(config_path)
            self.device_manager = EnhancedDeviceManager()
            self.recorder = EnhancedAudioRecorder(self.settings)
            self.uploader = FileUploader(self.settings)
            self.is_recording = False
            
            # 设置录音器状态回调
            self.recorder.set_status_callback(self.on_recorder_status)
            
            self.setup_ui()
            self.load_devices()
        except Exception as e:
            print(f"初始化错误: {e}")
            self.setup_ui()
            self.log_message(f"初始化错误: {e}")
        
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 设备选择区域 - 增强版
        device_frame = ttk.LabelFrame(main_frame, text="智能设备选择", padding="10")
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
        
        # 设备状态显示
        status_frame = tk.Frame(device_frame)
        status_frame.pack(fill=tk.X, pady=(5, 0))
        self.device_status_var = tk.StringVar(value="设备检测中...")
        ttk.Label(status_frame, textvariable=self.device_status_var, foreground="blue").pack(side=tk.LEFT)
        
        # 刷新设备按钮
        ttk.Button(status_frame, text="刷新设备", command=self.refresh_devices).pack(side=tk.RIGHT)
        
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
        
        # 录音控制区域
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(pady=(0, 10))
        
        self.record_btn = ttk.Button(control_frame, text="开始录音", command=self.toggle_recording)
        self.record_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 录音状态显示
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(control_frame, textvariable=self.status_var, foreground="green")
        self.status_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 录音时长显示
        self.duration_var = tk.StringVar(value="00:00")
        ttk.Label(control_frame, textvariable=self.duration_var).pack(side=tk.LEFT)
        
        # 录音信息显示
        info_display_frame = ttk.LabelFrame(main_frame, text="录音日志", padding="10")
        info_display_frame.pack(fill=tk.BOTH, expand=True)
        
        text_frame = tk.Frame(info_display_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.info_text = tk.Text(text_frame, height=10, width=70)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=scrollbar.set)
        
        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def load_devices(self):
        """加载设备 - 增强版"""
        try:
            # 获取推荐设备
            recommendations = self.device_manager.get_recommended_devices()
            
            # 加载物理麦克风设备
            physical_mics = self.device_manager.get_physical_microphones()
            mic_options = []
            for device_id, device in physical_mics:
                available = self.device_manager.test_device_availability(device_id)
                status = "✅" if available else "❌"
                mic_options.append(f"{status} [{device_id}] {device['name']}")
            
            self.mic_combo['values'] = mic_options
            
            # 加载回环设备
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
            
            # 更新设备状态
            mic_count = len([opt for opt in mic_options if "✅" in opt])
            system_count = len([opt for opt in system_options if "✅" in opt])
            
            if mic_count > 0 and system_count > 0:
                self.device_status_var.set(f"✅ 设备就绪 - 麦克风:{mic_count}个, 系统音频:{system_count}个")
            elif mic_count > 0:
                self.device_status_var.set(f"⚠️ 仅麦克风可用 - 请安装VB-Cable或启用立体声混音")
            else:
                self.device_status_var.set(f"❌ 无可用设备")
            
            self.log_message(f"设备加载完成 - 麦克风:{len(mic_options)}个, 系统音频:{len(system_options)}个")
            
        except Exception as e:
            self.log_message(f"设备加载失败: {e}")
            self.device_status_var.set("❌ 设备加载失败")
    
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
    
    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        mic_id = self.get_selected_device_id(self.mic_var.get())
        system_id = self.get_selected_device_id(self.system_var.get())
        
        if mic_id is None:
            messagebox.showerror("错误", "请选择可用的麦克风设备")
            return
        
        if system_id is None:
            if not messagebox.askyesno("确认", "未选择系统音频设备，将只录制麦克风。是否继续？"):
                return
        
        if not self.agent_phone.get().strip():
            if not messagebox.askyesno("确认", "未填写坐席手机号，是否继续录音？"):
                return
        
        def record_thread():
            try:
                if self.recorder.start_recording(mic_id, system_id):
                    self.is_recording = True
                    self.root.after(0, self.update_recording_ui, True)
                    self.root.after(0, self.start_duration_timer)
                else:
                    self.root.after(0, messagebox.showerror, "错误", "无法开始录音")
            except Exception as e:
                self.root.after(0, messagebox.showerror, "错误", f"录音失败: {str(e)}")
        
        threading.Thread(target=record_thread, daemon=True).start()
    
    def stop_recording(self):
        def stop_thread():
            try:
                result = self.recorder.stop_recording()
                self.is_recording = False
                self.root.after(0, self.update_recording_ui, False)
                
                if result:
                    self.root.after(0, self.process_recording_result, result)
                else:
                    self.root.after(0, self.log_message, "❌ 录音失败")
            except Exception as e:
                self.is_recording = False
                self.root.after(0, self.update_recording_ui, False)
                self.root.after(0, messagebox.showerror, "错误", f"停止录音失败: {str(e)}")
        
        threading.Thread(target=stop_thread, daemon=True).start()
    
    def process_recording_result(self, result):
        """处理录音结果"""
        # 重命名文件
        new_mic_file = None
        new_system_file = None
        
        if result['mic_success'] and result['mic_file']:
            new_mic_file = os.path.join(os.path.dirname(result['mic_file']), self.generate_filename("mic"))
            os.rename(result['mic_file'], new_mic_file)
            self.log_message(f"✅ 麦克风文件: {os.path.basename(new_mic_file)}")
        
        if result['speaker_success'] and result['speaker_file']:
            new_system_file = os.path.join(os.path.dirname(result['speaker_file']), self.generate_filename("system"))
            os.rename(result['speaker_file'], new_system_file)
            self.log_message(f"✅ 系统音频文件: {os.path.basename(new_system_file)}")
        
        self.log_message(f"录音完成! 时长: {result['duration']:.2f} 秒")
        
        # 上传文件
        if new_mic_file or new_system_file:
            call_info = {
                'agent_phone': self.agent_phone.get(),
                'customer_name': self.customer_name.get(),
                'customer_id': self.customer_id.get()
            }
            self.log_message("开始上传文件...")
            self.uploader.upload_files(new_mic_file, new_system_file, call_info, self.upload_callback)
    
    def start_duration_timer(self):
        """开始录音时长计时器"""
        if self.is_recording:
            status = self.recorder.get_recording_status()
            if status['recording']:
                duration = int(status['duration'])
                minutes = duration // 60
                seconds = duration % 60
                self.duration_var.set(f"{minutes:02d}:{seconds:02d}")
            
            # 每秒更新一次
            self.root.after(1000, self.start_duration_timer)
    
    def update_recording_ui(self, recording):
        if recording:
            self.record_btn.config(text="停止录音")
            self.status_var.set("录音中...")
            self.status_label.config(foreground="red")
        else:
            self.record_btn.config(text="开始录音")
            self.status_var.set("就绪")
            self.status_label.config(foreground="green")
            self.duration_var.set("00:00")
    
    def on_recorder_status(self, message):
        """录音器状态回调"""
        self.root.after(0, self.log_message, message)
    
    def upload_callback(self, success, message):
        self.root.after(0, self.log_message, message)
    
    def generate_filename(self, file_type):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        parts = []
        
        agent = self.agent_phone.get().strip()
        if agent:
            parts.append(f"Agent_{agent}")
        
        customer_name = self.customer_name.get().strip()
        customer_id = self.customer_id.get().strip()
        
        if customer_name:
            parts.append(f"Customer_{customer_name}")
        if customer_id:
            parts.append(f"ID_{customer_id}")
        
        if parts:
            filename = f"{file_type}_{timestamp}_{'_'.join(parts)}.wav"
        else:
            filename = f"{file_type}_{timestamp}.wav"
        
        return filename
    
    def log_message(self, message):
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.info_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.info_text.see(tk.END)
        except:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = EnhancedRecorderUI()
    app.run()