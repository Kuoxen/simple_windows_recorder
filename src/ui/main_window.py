import tkinter as tk
from tkinter import ttk, messagebox
import threading
from datetime import datetime
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Settings
from audio.device_manager import DeviceManager
from audio.recorder import AudioRecorder
from storage.uploader import FileUploader

class RecorderUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("呼叫中心录音系统")
        self.root.geometry("500x400")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 初始化组件
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config.yaml")
            self.settings = Settings(config_path)
            self.device_manager = DeviceManager()
            self.recorder = AudioRecorder(self.settings)
            self.uploader = FileUploader(self.settings)
            self.is_recording = False
            
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
        
        # 设备选择区域
        device_frame = ttk.LabelFrame(main_frame, text="设备选择", padding="10")
        device_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 麦克风选择
        mic_frame = tk.Frame(device_frame)
        mic_frame.pack(fill=tk.X, pady=2)
        ttk.Label(mic_frame, text="麦克风设备:").pack(side=tk.LEFT)
        self.mic_var = tk.StringVar()
        self.mic_combo = ttk.Combobox(mic_frame, textvariable=self.mic_var, width=40, state="readonly")
        self.mic_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
        # 系统音频选择
        system_frame = tk.Frame(device_frame)
        system_frame.pack(fill=tk.X, pady=2)
        ttk.Label(system_frame, text="系统音频:").pack(side=tk.LEFT)
        self.system_var = tk.StringVar()
        self.system_combo = ttk.Combobox(system_frame, textvariable=self.system_var, width=40, state="readonly")
        self.system_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
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
        
        # 状态显示
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(control_frame, textvariable=self.status_var, foreground="green")
        self.status_label.pack(side=tk.LEFT)
        
        # 录音信息显示
        info_display_frame = ttk.LabelFrame(main_frame, text="录音信息", padding="10")
        info_display_frame.pack(fill=tk.BOTH, expand=True)
        
        text_frame = tk.Frame(info_display_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.info_text = tk.Text(text_frame, height=8, width=60)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=scrollbar.set)
        
        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def load_devices(self):
        try:
            # 加载麦克风设备
            input_devices = self.device_manager.get_input_devices()
            mic_options = []
            for idx, device in input_devices:
                name = device['name']
                if not any(keyword in name.lower() for keyword in ['cable output', 'stereo mix', '立体声混音']):
                    mic_options.append(f"[{idx}] {name}")
            
            self.mic_combo['values'] = mic_options
            if mic_options:
                self.mic_combo.current(0)
            
            # 加载系统音频设备
            system_options = []
            for idx, device in input_devices:
                name = device['name'].lower()
                if any(keyword in name for keyword in ['cable output', 'stereo mix', '立体声混音', '混音', 'blackhole', 'soundflower']):
                    system_options.append(f"[{idx}] {device['name']}")
            
            self.system_combo['values'] = system_options
            if system_options:
                self.system_combo.current(0)
            
            self.log_message(f"设备加载完成 - 麦克风:{len(mic_options)}个, 系统音频:{len(system_options)}个")
            
        except Exception as e:
            self.log_message(f"设备加载失败: {e}")
            # 设置空的选项以防止界面崩溃
            self.mic_combo['values'] = ["无可用设备"]
            self.system_combo['values'] = ["无可用设备"]
        
    def get_selected_device_id(self, combo_value):
        if not combo_value:
            return None
        # 提取 [ID] 中的数字
        try:
            return int(combo_value.split(']')[0][1:])
        except:
            return None
    
    def generate_filename(self, file_type):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 构建文件名
        parts = []
        
        # 坐席手机号
        agent = self.agent_phone.get().strip()
        if agent:
            parts.append(f"Agent_{agent}")
        
        # 客户信息
        customer_name = self.customer_name.get().strip()
        customer_id = self.customer_id.get().strip()
        
        if customer_name:
            parts.append(f"Customer_{customer_name}")
        if customer_id:
            parts.append(f"ID_{customer_id}")
        
        # 组合文件名
        if parts:
            filename = f"{file_type}_{timestamp}_{'_'.join(parts)}.wav"
        else:
            filename = f"{file_type}_{timestamp}.wav"
        
        return filename
    
    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        # 获取选择的设备
        mic_id = self.get_selected_device_id(self.mic_var.get())
        system_id = self.get_selected_device_id(self.system_var.get())
        
        if mic_id is None:
            messagebox.showerror("错误", "请选择麦克风设备")
            return
        
        if system_id is None:
            messagebox.showerror("错误", "请选择系统音频设备")
            return
        
        # 检查坐席手机号
        if not self.agent_phone.get().strip():
            if not messagebox.askyesno("确认", "未填写坐席手机号，是否继续录音？"):
                return
        
        # 开始录音
        def record_thread():
            try:
                if self.recorder.start_recording(mic_id, system_id):
                    self.is_recording = True
                    self.root.after(0, self.update_recording_ui, True)
                    self.root.after(0, self.log_message, f"开始录音 - 麦克风:[{mic_id}] 系统音频:[{system_id}]")
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
                    # 检查文件是否存在
                    old_mic_file = result.get('mic_file')
                    old_system_file = result.get('speaker_file')
                    
                    new_mic_file = None
                    new_system_file = None
                    
                    # 处理麦克风文件
                    if old_mic_file and os.path.exists(old_mic_file):
                        new_mic_file = os.path.join(os.path.dirname(old_mic_file), self.generate_filename("mic"))
                        os.rename(old_mic_file, new_mic_file)
                        self.root.after(0, self.log_message, f"麦克风文件: {os.path.basename(new_mic_file)}")
                    else:
                        self.root.after(0, self.log_message, "⚠️  麦克风录音失败")
                    
                    # 处理系统音频文件
                    if old_system_file and os.path.exists(old_system_file):
                        new_system_file = os.path.join(os.path.dirname(old_system_file), self.generate_filename("system"))
                        os.rename(old_system_file, new_system_file)
                        self.root.after(0, self.log_message, f"系统音频文件: {os.path.basename(new_system_file)}")
                    else:
                        self.root.after(0, self.log_message, "⚠️  系统音频录音失败 - 请检查VB-Cable设置")
                    
                    self.root.after(0, self.log_message, f"录音完成! 时长: {result.get('duration', 0):.2f} 秒")
                    
                    # 提交后处理
                    if new_mic_file or new_system_file:
                        call_info = {
                            'agent_phone': self.agent_phone.get(),
                            'customer_name': self.customer_name.get(),
                            'customer_id': self.customer_id.get()
                        }
                        result_updated = {
                            'mic_file': new_mic_file,
                            'speaker_file': new_system_file,
                            'duration': result.get('duration', 0)
                        }
                        self.root.after(0, self.log_message, "提交后处理...")
                        self.recorder.submit_for_post_processing(result_updated, call_info)
                    else:
                        self.root.after(0, self.log_message, "❌ 没有文件可处理")
                else:
                    self.root.after(0, self.log_message, "❌ 录音失败 - 未能生成录音文件")
            except Exception as e:
                self.is_recording = False
                self.root.after(0, self.update_recording_ui, False)
                self.root.after(0, messagebox.showerror, "错误", f"停止录音失败: {str(e)}")
        
        threading.Thread(target=stop_thread, daemon=True).start()
    
    def update_recording_ui(self, recording):
        if recording:
            self.record_btn.config(text="停止录音", style="Accent.TButton")
            self.status_var.set("录音中...")
            self.status_label.config(foreground="red")
        else:
            self.record_btn.config(text="开始录音")
            self.status_var.set("就绪")
            self.status_label.config(foreground="green")
    
    def upload_callback(self, success, message):
        """上传结果回调"""
        self.root.after(0, self.log_message, message)
        if success:
            self.root.after(0, self.log_message, "✅ 文件上传成功")
        else:
            self.root.after(0, self.log_message, "❌ 文件上传失败")
    
    def log_message(self, message):
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.info_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.info_text.see(tk.END)
        except:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    
    def on_closing(self):
        """窗口关闭事件处理"""
        if self.is_recording:
            if messagebox.askokcancel("退出", "正在录音中，确定要退出吗？"):
                self.recorder.stop_post_processor()
                self.root.destroy()
        else:
            self.recorder.stop_post_processor()
            self.root.destroy()
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = RecorderUI()
    app.run()