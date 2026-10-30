"""A-3 呼救声/尖叫检测。

判定逻辑：
1. 音频能量突发（is_burst）
2. 频谱质心偏高（尖叫是高频）
3. 持续 scream_confirm_seconds 秒 → 触发警报
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
import threading

from ..detect.audio import AudioFeatures

logger = logging.getLogger(__name__)

# 配置常量
DEFAULT_CONFIRM_SECONDS = 2        # 持续多久确认呼救
DEFAULT_HIGH_FREQ_CENTROID = 1500.0 # 频谱质心高于此值算"高频"
DEFAULT_MIN_RMS = 0.08              # 最小能量阈值


@dataclass
class ScreamState:
    is_screaming: bool = False
    scream_start_time: float = 0.0
    scream_duration: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


class ScreamDetector:
    def __init__(
        self,
        scream_confirm_seconds: int = DEFAULT_CONFIRM_SECONDS,
        high_freq_centroid: float = DEFAULT_HIGH_FREQ_CENTROID,
        min_rms: float = DEFAULT_MIN_RMS,
    ) -> None:
        self.scream_confirm_seconds = scream_confirm_seconds
        self.high_freq_centroid = high_freq_centroid
        self.min_rms = min_rms
        self.state = ScreamState()

    def update(self, features: AudioFeatures) -> bool:
        """每块音频更新一次，返回是否触发呼救警报。"""
        now = time.monotonic()

        # 呼救特征：能量够大 + 高频
        is_scream = (
            features.rms > self.min_rms
            and features.spectral_centroid > self.high_freq_centroid
        )

        with self.state.lock:
            if is_scream:
                if not self.state.is_screaming:
                    self.state.is_screaming = True
                    self.state.scream_start_time = now
                    logger.info(
                        "疑似呼救：rms=%.3f, centroid=%.0fHz",
                        features.rms, features.spectral_centroid,
                    )

                elapsed = now - self.state.scream_start_time
                self.state.scream_duration = elapsed

                if elapsed >= self.scream_confirm_seconds:
                    logger.warning("确认呼救！持续 %.1f 秒", elapsed)
                    self._reset_locked()
                    return True
            else:
                if self.state.is_screaming:
                    logger.info("呼救结束")
                self._reset_locked()

        return False

    def _reset_locked(self) -> None:
        self.state.is_screaming = False
        self.state.scream_start_time = 0.0
        self.state.scream_duration = 0.0
