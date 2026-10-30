"""音频检测：轻量版音频特征提取。

阶段先用 RMS 能量 + 频谱质心做粗判，不引入 TF/YAMNet 重依赖，
跑通端到端链路后再升级为 YAMNet 分类。

输出：音频块的能量、频谱质心、是否突发。
后续替换 YAMNet 时，只需在 extract() 里追加模型推理，接口不变。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AudioFeatures:
    """一段音频的特征。

    预留 yamnet_categories / yamnet_scores 字段，后续接入 YAMNet 时直接填充。
    """

    rms: float               # 均方根能量（0~1）
    spectral_centroid: float  # 频谱质心（Hz），越高越尖锐
    is_burst: bool           # 是否突发高能量
    duration_sec: float      # 时长（秒）
    # YAMNet 预留字段（后续填充，不影响当前逻辑）
    yamnet_categories: list[str] | None = None
    yamnet_scores: list[float] | None = None


class AudioDetector:
    """音频特征检测器。"""

    def __init__(
        self,
        sample_rate: int = 16000,
        burst_threshold: float = 0.1,     # RMS 超过此值算"大声音"
        burst_increase_ratio: float = 3.0,  # 相对背景能量的倍数，算"突发"
        background_ema_alpha: float = 0.01,  # 背景能量滑动平均系数
    ) -> None:
        self.sample_rate = sample_rate
        self.burst_threshold = burst_threshold
        self.burst_increase_ratio = burst_increase_ratio
        self.background_ema_alpha = background_ema_alpha
        self._background_rms = 0.01  # 背景能量估计，滑动更新

    def extract(self, audio: np.ndarray) -> AudioFeatures:
        """提取一段音频的特征。audio 是 16kHz float32 单声道。

        后续接入 YAMNet 时，在此方法末尾追加模型推理，填充 yamnet_* 字段即可。
        """
        if len(audio) == 0:
            return AudioFeatures(0.0, 0.0, False, 0.0)

        # RMS 能量
        rms = float(np.sqrt(np.mean(audio ** 2)))

        # 频谱质心（FFT）
        n = len(audio)
        fft = np.abs(np.fft.rfft(audio * np.hanning(n)))
        freqs = np.fft.rfftfreq(n, 1.0 / self.sample_rate)
        if np.sum(fft) > 0:
            centroid = float(np.sum(freqs * fft) / np.sum(fft))
        else:
            centroid = 0.0

        # 是否突发：能量超过阈值 且 远大于背景
        is_burst = rms > self.burst_threshold and rms > self._background_rms * self.burst_increase_ratio

        # 背景能量滑动更新（EMA），持续适应环境，不做 if 限制
        self._background_rms = (
            (1 - self.background_ema_alpha) * self._background_rms
            + self.background_ema_alpha * rms
        )

        duration = len(audio) / self.sample_rate

        return AudioFeatures(
            rms=rms,
            spectral_centroid=centroid,
            is_burst=is_burst,
            duration_sec=duration,
        )
