"""环形音频缓冲：保存最近 N 秒的音频块。

触发警报时，和视频片段一起保存（音频+视频对齐）。
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BufferedAudio:
    timestamp: float
    block: np.ndarray  # float32 单声道，16kHz


class AudioRingBuffer:
    """环形音频缓冲（线程安全）。"""

    def __init__(self, max_seconds: float = 30.0, block_seconds: float = 0.5) -> None:
        self.max_seconds = max_seconds
        self.block_seconds = block_seconds
        self.max_blocks = int(max_seconds / block_seconds)
        self._buffer: deque[BufferedAudio] = deque(maxlen=self.max_blocks)
        self._lock = threading.Lock()

    def append(self, block: np.ndarray) -> None:
        with self._lock:
            self._buffer.append(BufferedAudio(time.monotonic(), block.copy()))

    def snapshot(self) -> list[BufferedAudio]:
        with self._lock:
            return list(self._buffer)

    def concatenate(self) -> np.ndarray:
        """把缓冲里的音频块拼成一整条。"""
        with self._lock:
            if not self._buffer:
                return np.array([], dtype=np.float32)
            return np.concatenate([bf.block for bf in self._buffer])


def save_audio_wav(audio: np.ndarray, sample_rate: int, filepath: str) -> None:
    """保存为 WAV 文件（不依赖 scipy，用标准库 wave 模块）。"""
    import wave
    import struct

    Path(filepath).parent.mkdir(parents=True, exist_ok=True)

    # float32 → int16
    audio_int16 = np.clip(audio, -1.0, 1.0)
    audio_int16 = (audio_int16 * 32767).astype(np.int16)

    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())

    logger.info("音频已保存：%s（%.1f 秒）", filepath, len(audio) / sample_rate)
