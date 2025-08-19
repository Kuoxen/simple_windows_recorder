import numpy as np
import time
from typing import Dict, Any
import logging

class AudioActivityDetector:
    """音频活动检测器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.volume_threshold = config.get('volume_threshold', 0.015)
        self.start_duration = config.get('start_duration', 3.0)
        self.end_silence_duration = config.get('end_silence_duration', 12.0)
        self.min_call_duration = config.get('min_call_duration', 5.0)
        self.check_interval = config.get('check_interval', 0.5)
        
        # 状态跟踪
        self.mic_active_start = None
        self.system_active_start = None
        self.last_activity_time = None
        self.call_start_time = None
        
        self.logger = logging.getLogger(__name__)
    
    def detect_activity(self, audio_data: np.ndarray) -> bool:
        """检测音频是否活跃"""
        if len(audio_data) == 0:
            return False
        
        # 计算RMS音量
        rms = np.sqrt(np.mean(audio_data**2))
        return rms > self.volume_threshold
    
    def update_mic_activity(self, audio_data: np.ndarray) -> bool:
        """更新麦克风活动状态"""
        current_time = time.time()
        is_active = self.detect_activity(audio_data)
        
        if is_active:
            if self.mic_active_start is None:
                self.mic_active_start = current_time
            self.last_activity_time = current_time
        else:
            self.mic_active_start = None
        
        return is_active
    
    def update_system_activity(self, audio_data: np.ndarray) -> bool:
        """更新系统音频活动状态"""
        current_time = time.time()
        is_active = self.detect_activity(audio_data)
        
        if is_active:
            if self.system_active_start is None:
                self.system_active_start = current_time
            self.last_activity_time = current_time
        else:
            self.system_active_start = None
        
        return is_active
    
    def should_start_recording(self) -> bool:
        """判断是否应该开始录制"""
        current_time = time.time()
        
        # 检查双路音频是否都活跃且持续足够时间
        if (self.mic_active_start is not None and 
            self.system_active_start is not None):
            
            mic_duration = current_time - self.mic_active_start
            system_duration = current_time - self.system_active_start
            
            if (mic_duration >= self.start_duration and 
                system_duration >= self.start_duration):
                return True
        
        return False
    
    def should_stop_recording(self) -> bool:
        """判断是否应该停止录制"""
        if self.last_activity_time is None:
            return False
        
        current_time = time.time()
        silence_duration = current_time - self.last_activity_time
        
        # 检查静默时间是否超过阈值
        if silence_duration >= self.end_silence_duration:
            # 检查通话时长是否满足最小要求
            if self.call_start_time is not None:
                call_duration = current_time - self.call_start_time
                return call_duration >= self.min_call_duration
        
        return False
    
    def start_call(self):
        """标记通话开始"""
        self.call_start_time = time.time()
        self.logger.info("通话开始")
    
    def end_call(self) -> float:
        """标记通话结束，返回通话时长"""
        if self.call_start_time is None:
            return 0.0
        
        duration = time.time() - self.call_start_time
        self.call_start_time = None
        self.mic_active_start = None
        self.system_active_start = None
        self.last_activity_time = None
        
        self.logger.info(f"通话结束，时长: {duration:.2f}秒")
        return duration
    
    def get_status(self) -> Dict[str, Any]:
        """获取检测器状态"""
        current_time = time.time()
        
        return {
            'mic_active': self.mic_active_start is not None,
            'system_active': self.system_active_start is not None,
            'mic_active_duration': current_time - self.mic_active_start if self.mic_active_start else 0,
            'system_active_duration': current_time - self.system_active_start if self.system_active_start else 0,
            'silence_duration': current_time - self.last_activity_time if self.last_activity_time else 0,
            'call_duration': current_time - self.call_start_time if self.call_start_time else 0,
            'volume_threshold': self.volume_threshold
        }