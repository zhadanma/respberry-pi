"""采集抽象层。

开发期实现：OpenCV（USB / 内置摄像头）+ sounddevice（PC 麦克风）。
部署期只需新增 picamera2 实现，上层逻辑不动（P7 迁移）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class CameraSource(ABC):
    """摄像头统一接口。映射为 BGR 帧（OpenCV 惯例）。"""

    name: str = "unknown"

    @abstractmethod
    def start(self) -> None:
        """打开设备，失败时抛 RuntimeError。"""

    @abstractmethod
    def read(self) -> np.ndarray | None:
        """取一帧 BGR 图像；暂时取不到时返回 None。"""

    @abstractmethod
    def close(self) -> None:
        """释放设备，可重复调用。"""


class MicrophoneSource(ABC):
    """麦克风统一接口。输出 float32 单声道采样块。"""

    name: str = "unknown"

    @abstractmethod
    def start(self) -> None:
        """打开设备，失败时抛 RuntimeError。"""

    @abstractmethod
    def read(self, timeout: float = 1.0) -> np.ndarray | None:
        """取一块音频；超时返回 None。"""

    @abstractmethod
    def close(self) -> None:
        """释放设备，可重复调用。"""

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        """采样率（Hz）。"""
