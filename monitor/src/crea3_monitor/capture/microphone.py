"""sounddevice 麦克风实现（开发期：PC 麦克风）。

阶段一仅提供接口实现，主循环不启用采集；P3 音频检测时接入。
"""

from __future__ import annotations

import logging
import queue

import numpy as np
import sounddevice as sd

from .base import MicrophoneSource

logger = logging.getLogger(__name__)


class SoundDeviceMicrophone(MicrophoneSource):
    name = "sounddevice"

    def __init__(
        self,
        sample_rate: int = 16000,
        block_seconds: float = 0.5,
        device: int | None = None,
    ) -> None:
        self._sample_rate = sample_rate
        self._block_frames = max(1, int(sample_rate * block_seconds))
        self._device = device
        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=8)
        self._stream: sd.InputStream | None = None

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def start(self) -> None:
        def on_audio(indata: np.ndarray, frames: int, time_info, status) -> None:
            if status:
                logger.warning("音频采集状态：%s", status)
            block = indata[:, 0].copy()
            try:
                self._queue.put_nowait(block)
            except queue.Full:
                # 下游处理不过来时丢掉最旧的一块，避免延迟累积
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass
                self._queue.put_nowait(block)

        try:
            stream = sd.InputStream(
                samplerate=self._sample_rate,
                blocksize=self._block_frames,
                channels=1,
                dtype="float32",
                device=self._device,
                callback=on_audio,
            )
            stream.start()
        except Exception as exc:  # sounddevice 抛出的异常类型不稳定
            raise RuntimeError(f"无法打开麦克风：{exc}") from exc
        self._stream = stream
        logger.info("麦克风已打开：采样率=%sHz", self._sample_rate)

    def read(self, timeout: float = 1.0) -> np.ndarray | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            logger.info("麦克风已释放")
