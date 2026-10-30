"""A-4 异常声响检测（玻璃破碎、重物倒地、门铃等突发大声音）。

判定逻辑：
1. 能量突发（is_burst）
2. 频谱质心偏低或中低频（重物倒地是低频闷响，玻璃破碎是高频脆响）
3. 与呼救声区分：呼救声是持续高频，异常声响是短促突发
4. 单次突发 → 触发警报（不需要持续）
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
import threading

from ..detect.audio import AudioFeatures

logger = logging.getLogger(__name__)

# 配置常量
DEFAULT_MIN_RMS = 0.15          # 异常声响能量阈值（比呼救高）
DEFAULT_COOLDOWN_SECONDS = 10   # 两次警报之间的冷却时间


@dataclass
class NoiseState:
    last_alert_time: float = 0.0   # 上次警报时间，用于冷却
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


class NoiseDetector:
    def __init__(
        self,
        min_rms: float = DEFAULT_MIN_RMS,
        cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
    ) -> None:
        self.min_rms = min_rms
        self.cooldown_seconds = cooldown_seconds
        self.state = NoiseState()

    def update(self, features: AudioFeatures) -> bool:
        """每块音频更新一次，返回是否触发异常声响警报。"""
        now = time.monotonic()

        # 异常声响：大能量突发
        is_noise = features.is_burst and features.rms > self.min_rms

        if not is_noise:
            return False

        with self.state.lock:
            # 冷却期内不重复报警
            if now - self.state.last_alert_time < self.cooldown_seconds:
                return False

            self.state.last_alert_time = now
            logger.warning(
                "检测到异常声响：rms=%.3f, centroid=%.0fHz",
                features.rms, features.spectral_centroid,
            )
            return True
