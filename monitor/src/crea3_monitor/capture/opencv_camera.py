"""OpenCV 摄像头实现（开发期：PC 的 USB / 内置摄像头）。"""

from __future__ import annotations

import logging
import sys

import cv2
import numpy as np

from .base import CameraSource

logger = logging.getLogger(__name__)


class OpenCVCamera(CameraSource):
    name = "opencv"

    def __init__(self, index: int, width: int, height: int, fps: int) -> None:
        self.index = index
        self.width = width
        self.height = height
        self.fps = fps
        self._capture: cv2.VideoCapture | None = None

    def start(self) -> None:
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        capture = cv2.VideoCapture(self.index, backend)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"无法打开摄像头 index={self.index}（可能被其他程序占用）")
        # MJPG 能明显提高 USB 摄像头在高分辨率下的实际帧率
        capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        capture.set(cv2.CAP_PROP_FPS, self.fps)
        actual_w = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self._capture = capture
        logger.info("摄像头已打开：index=%s 实际分辨率=%sx%s", self.index, actual_w, actual_h)

    def read(self) -> np.ndarray | None:
        if self._capture is None:
            return None
        ok, frame = self._capture.read()
        if not ok or frame is None:
            return None
        return frame

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
            logger.info("摄像头已释放")
