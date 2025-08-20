import os
import wave
import numpy as np
import threading
from queue import Queue
from datetime import datetime
import logging
from typing import Dict, Any, Optional, Tuple

class AudioPostProcessor:
    """音频后处理器 - 验证、合并、上传录音文件"""
    
    def __init__(self, settings):
        self.settings = settings
        self.config = settings.post_processing
        self.processing_queue = Queue()
        self.worker_thread = None
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        """启动后处理器"""
        if self.is_running:
            return
            
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._process_worker, daemon=True)
        self.worker_thread.start()
        self.logger.info("音频后处理器已启动")
    
    def stop(self):
        """停止后处理器"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
        self.logger.info("音频后处理器已停止")
    
    def submit_recording(self, mic_file: str, system_file: str, call_info: Dict[str, Any]):
        """提交录音文件进行后处理"""
        session_data = {
            'mic_file': mic_file,
            'system_file': system_file,
            'call_info': call_info,
            'timestamp': datetime.now()
        }
        self.processing_queue.put(session_data)
        self.logger.info(f"录音文件已提交后处理: {os.path.basename(mic_file) if mic_file else 'None'}, {os.path.basename(system_file) if system_file else 'None'}")
    
    def _process_worker(self):
        """后处理工作线程"""
        while self.is_running:
            try:
                session_data = self.processing_queue.get(timeout=1.0)
                self._process_recording(session_data)
            except:
                continue
    
    def _process_recording(self, session_data: Dict[str, Any]):
        """处理单个录音会话"""
        mic_file = session_data['mic_file']
        system_file = session_data['system_file']
        call_info = session_data['call_info']
        
        try:
            self.logger.info(f"开始处理录音: {os.path.basename(mic_file) if mic_file else 'None'}")
            
            # 1. 检测时长
            duration = self._get_audio_duration(mic_file or system_file)
            if duration < self.config.get('min_duration', 5.0):
                self.logger.info(f"录音时长过短({duration:.1f}s)，标记为无效")
                self._cleanup_invalid(mic_file, system_file)
                return
            
            # 2. 检测单侧静音
            if self._is_single_side_silent(mic_file, system_file):
                self.logger.info("检测到单侧静音，标记为无效")
                self._cleanup_invalid(mic_file, system_file)
                return
            
            # 3. 合并为双声道
            merged_file = self._merge_to_stereo(mic_file, system_file, call_info)
            if not merged_file:
                self.logger.error("文件合并失败")
                return
            
            # 4. 上传OSS
            if self.settings.upload.get('enabled', False):
                self._upload_merged_file(merged_file, call_info)
            
            # 5. 清理原始文件
            if not self.config.get('keep_original', False):
                self._cleanup_original(mic_file, system_file)
                
            self.logger.info(f"录音处理完成: {os.path.basename(merged_file)}")
            
        except Exception as e:
            self.logger.error(f"录音处理失败: {e}")
    
    def _get_audio_duration(self, audio_file: str) -> float:
        """获取音频文件时长"""
        if not audio_file or not os.path.exists(audio_file):
            return 0.0
        
        try:
            with wave.open(audio_file, 'rb') as wf:
                frames = wf.getnframes()
                sample_rate = wf.getframerate()
                return frames / sample_rate
        except Exception as e:
            self.logger.error(f"获取音频时长失败: {e}")
            return 0.0
    
    def _is_single_side_silent(self, mic_file: str, system_file: str) -> bool:
        """检测是否单侧静音"""
        mic_silent = self._is_audio_silent(mic_file)
        system_silent = self._is_audio_silent(system_file)
        
        # 如果任一侧全程静音，认为是无效录制
        return mic_silent or system_silent
    
    def _is_audio_silent(self, audio_file: str) -> bool:
        """检测音频文件是否基本无声"""
        if not audio_file or not os.path.exists(audio_file):
            return True
        
        try:
            with wave.open(audio_file, 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            
            if len(audio_data) == 0:
                return True
            
            # 计算静音帧比例
            threshold = self.config.get('silence_threshold', 0.001)
            silence_ratio = self.config.get('silence_ratio', 0.95)
            
            frame_size = 1024
            silent_frames = 0
            total_frames = len(audio_data) // frame_size
            
            for i in range(total_frames):
                frame = audio_data[i*frame_size:(i+1)*frame_size]
                if np.sqrt(np.mean(frame**2)) < threshold:
                    silent_frames += 1
            
            if total_frames == 0:
                return True
                
            return (silent_frames / total_frames) > silence_ratio
            
        except Exception as e:
            self.logger.error(f"检测音频静音失败: {e}")
            return True
    
    def _merge_to_stereo(self, mic_file: str, system_file: str, call_info: Dict[str, Any]) -> Optional[str]:
        """合并为双声道文件"""
        try:
            # 读取音频数据
            mic_data = self._read_audio_file(mic_file) if mic_file else None
            system_data = self._read_audio_file(system_file) if system_file else None
            
            if mic_data is None and system_data is None:
                return None
            
            # 确定最大长度
            max_length = 0
            if mic_data is not None:
                max_length = max(max_length, len(mic_data))
            if system_data is not None:
                max_length = max(max_length, len(system_data))
            
            # 填充到相同长度
            if mic_data is None:
                mic_data = np.zeros(max_length, dtype=np.float32)
            elif len(mic_data) < max_length:
                mic_data = np.pad(mic_data, (0, max_length - len(mic_data)))
            
            if system_data is None:
                system_data = np.zeros(max_length, dtype=np.float32)
            elif len(system_data) < max_length:
                system_data = np.pad(system_data, (0, max_length - len(system_data)))
            
            # 合并为双声道 (左声道:mic, 右声道:system)
            stereo_data = np.column_stack((mic_data, system_data))
            
            # 生成合并文件名
            merged_filename = self._generate_merged_filename(mic_file or system_file, call_info)
            merged_path = os.path.join(self.settings.recording['output_dir'], merged_filename)
            
            # 保存双声道文件
            with wave.open(merged_path, 'wb') as wf:
                wf.setnchannels(2)  # 双声道
                wf.setsampwidth(2)
                wf.setframerate(self.settings.audio['sample_rate'])
                
                # 转换为int16并保存
                stereo_int16 = (stereo_data * 32767).astype(np.int16)
                wf.writeframes(stereo_int16.tobytes())
            
            self.logger.info(f"双声道文件合并完成: {merged_filename}")
            return merged_path
            
        except Exception as e:
            self.logger.error(f"合并双声道文件失败: {e}")
            return None
    
    def _read_audio_file(self, audio_file: str) -> Optional[np.ndarray]:
        """读取音频文件数据"""
        if not audio_file or not os.path.exists(audio_file):
            return None
        
        try:
            with wave.open(audio_file, 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        except Exception as e:
            self.logger.error(f"读取音频文件失败: {e}")
            return None
    
    def _generate_merged_filename(self, original_file: str, call_info: Dict[str, Any]) -> str:
        """生成合并文件名"""
        # 从原文件名提取时间戳
        basename = os.path.basename(original_file)
        if '_' in basename:
            parts = basename.split('_')
            if len(parts) >= 2:
                timestamp = f"{parts[-2]}_{parts[-1].split('.')[0]}"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 构建文件名
        filename_parts = ['merged', timestamp]
        
        if call_info.get('agent_phone'):
            filename_parts.extend(['Agent', call_info['agent_phone']])
        if call_info.get('customer_name'):
            filename_parts.extend(['Customer', call_info['customer_name']])
        if call_info.get('customer_id'):
            filename_parts.extend(['ID', call_info['customer_id']])
        
        return '_'.join(filename_parts) + '.wav'
    
    def _upload_merged_file(self, merged_file: str, call_info: Dict[str, Any]):
        """上传合并后的文件"""
        try:
            from storage.uploader import FileUploader
            uploader = FileUploader(self.settings)
            
            def upload_callback(success, message):
                if success:
                    self.logger.info(f"文件上传成功: {message}")
                else:
                    self.logger.error(f"文件上传失败: {message}")
            
            # 上传合并文件（作为mic_file参数传递）
            uploader.upload_files(merged_file, None, call_info, upload_callback)
            
        except Exception as e:
            self.logger.error(f"上传合并文件失败: {e}")
    
    def _cleanup_invalid(self, mic_file: str, system_file: str):
        """清理无效录音文件"""
        for file_path in [mic_file, system_file]:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    self.logger.info(f"已删除无效文件: {os.path.basename(file_path)}")
                except Exception as e:
                    self.logger.error(f"删除无效文件失败: {e}")
    
    def _cleanup_original(self, mic_file: str, system_file: str):
        """清理原始分离文件"""
        for file_path in [mic_file, system_file]:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    self.logger.info(f"已删除原始文件: {os.path.basename(file_path)}")
                except Exception as e:
                    self.logger.error(f"删除原始文件失败: {e}")