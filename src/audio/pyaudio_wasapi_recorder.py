import threading
import time
from typing import Callable, Optional

import numpy as np


class PyaudioWasapiLoopbackRecorder:
    """基于 PyAudioWPatch 的 WASAPI Loopback 录制器。

    不依赖立体声混音或虚拟声卡，直接录制默认扬声器的系统音频。
    """

    def __init__(self, sample_rate: Optional[int] = None, channels: Optional[int] = None):
        self.sample_rate = sample_rate
        self.channels = channels
        self._callback: Optional[Callable[[np.ndarray], None]] = None
        self._pyaudio = None
        self._stream = None
        self._device_info = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def set_audio_callback(self, callback: Callable[[np.ndarray], None]):
        self._callback = callback

    def start_recording(self) -> bool:
        try:
            import pyaudiowpatch as pyaudio
        except Exception:
            return False

        try:
            self._pyaudio = pyaudio.PyAudio()

            # 优先获取默认 WASAPI loopback 设备
            try:
                self._device_info = self._pyaudio.get_default_wasapi_loopback()
            except Exception:
                self._device_info = None

            # 回退：扫描 isLoopback 标记
            if not self._device_info:
                for i in range(self._pyaudio.get_device_count()):
                    info = self._pyaudio.get_device_info_by_index(i)
                    if info.get('isLoopback') and info.get('maxInputChannels', 0) > 0:
                        self._device_info = info
                        break

            if not self._device_info:
                return False

            device_index = int(self._device_info['index'])
            channels = int(self.channels or self._device_info.get('maxInputChannels', 2) or 2)

            # 优先尝试设备默认采样率，其次尝试常见可用采样率，使用 PortAudio 能力探测
            candidate_rates = []
            try:
                default_rate = int(self._device_info.get('defaultSampleRate'))
                if default_rate:
                    candidate_rates.append(default_rate)
            except Exception:
                pass
            # 如果外部指定了期望采样率，优先尝试
            if self.sample_rate and self.sample_rate not in candidate_rates:
                candidate_rates.insert(0, int(self.sample_rate))
            for r in [48000, 44100, 32000, 22050, 16000]:
                if r not in candidate_rates:
                    candidate_rates.append(r)

            rate = None
            for r in candidate_rates:
                try:
                    if self._pyaudio.is_format_supported(
                        rate=r,
                        input_device=device_index,
                        input_channels=channels,
                        input_format=pyaudio.paInt16,
                    ):
                        rate = r
                        break
                except Exception:
                    continue
            if rate is None:
                return False

            # 使用非阻塞回调流
            def _on_frames(in_data, frame_count, time_info, status):
                if self._callback and in_data:
                    # int16 -> float32 [-1,1]
                    audio = np.frombuffer(in_data, dtype=np.int16).astype(np.float32) / 32768.0
                    if channels > 1 and len(audio) % channels == 0:
                        audio = audio.reshape(-1, channels).mean(axis=1)
                    self._callback(audio)
                return (None, pyaudio.paContinue)

            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024,
                stream_callback=_on_frames,
            )

            self._running = True
            self._stream.start_stream()

            # 保持后台线程运行（用于与现有接口一致）
            def _spin():
                while self._running and self._stream.is_active():
                    time.sleep(0.05)

            self._thread = threading.Thread(target=_spin, daemon=True)
            self._thread.start()
            return True
        except Exception:
            self.stop_recording()
            return False

    def stop_recording(self):
        self._running = False
        try:
            if self._stream is not None:
                try:
                    if self._stream.is_active():
                        self._stream.stop_stream()
                finally:
                    self._stream.close()
        except Exception:
            pass
        finally:
            self._stream = None

        try:
            if self._pyaudio is not None:
                self._pyaudio.terminate()
        except Exception:
            pass
        finally:
            self._pyaudio = None


