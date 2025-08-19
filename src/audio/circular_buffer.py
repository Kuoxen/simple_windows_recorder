import numpy as np
from collections import deque
import threading

class CircularBuffer:
    """循环缓冲区，用于存储固定时长的音频数据"""
    
    def __init__(self, duration_seconds: float, sample_rate: int):
        self.sample_rate = sample_rate
        self.max_samples = int(duration_seconds * sample_rate)
        self.buffer = deque(maxlen=self.max_samples)
        self.lock = threading.Lock()
    
    def write(self, data: np.ndarray):
        """写入音频数据"""
        with self.lock:
            self.buffer.extend(data)
    
    def read_all(self) -> np.ndarray:
        """读取所有缓冲区数据"""
        with self.lock:
            return np.array(list(self.buffer), dtype=np.float32)
    
    def clear(self):
        """清空缓冲区"""
        with self.lock:
            self.buffer.clear()
    
    def get_duration(self) -> float:
        """获取当前缓冲区数据的时长（秒）"""
        with self.lock:
            return len(self.buffer) / self.sample_rate
    
    def is_full(self) -> bool:
        """检查缓冲区是否已满"""
        with self.lock:
            return len(self.buffer) >= self.max_samples