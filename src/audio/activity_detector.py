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
        # 不再立即重置，允许短暂停顿
        
        return is_active
    
    def update_system_activity(self, audio_data: np.ndarray) -> bool:
        """更新系统音频活动状态"""
        current_time = time.time()
        is_active = self.detect_activity(audio_data)
        
        if is_active:
            if self.system_active_start is None:
                self.system_active_start = current_time
            self.last_activity_time = current_time
        # 不再立即重置，允许短暂停顿
        
        return is_active
    
    def should_start_recording(self) -> bool:
        """判断是否应该开始录制"""
        current_time = time.time()
        
        # 检查是否需要重置活跃状态（静默超过5秒才重置）
        if self.last_activity_time is not None:
            silence_duration = current_time - self.last_activity_time
            if silence_duration > 5.0:  # 5秒静默才重置
                self.mic_active_start = None
                self.system_active_start = None
        
        # 检查是否有任意一路音频活跃超过阈值时间
        mic_active_duration = 0
        system_active_duration = 0
        
        if self.mic_active_start is not None:
            mic_active_duration = current_time - self.mic_active_start
        
        if self.system_active_start is not None:
            system_active_duration = current_time - self.system_active_start
        
        # 只要任意一路音频活跃超过阈值时间，就开始录制
        max_duration = max(mic_active_duration, system_active_duration)
        if max_duration >= self.start_duration:
            self.logger.info(f"检测到音频活动，开始录制 - 麦克风:{mic_active_duration:.1f}s, 系统音频:{system_active_duration:.1f}s")
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