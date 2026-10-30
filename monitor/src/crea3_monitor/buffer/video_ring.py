"""环形视频缓冲：保存最近 N 秒的帧。

触发警报时，把「前录 pre_seconds + 后录 post_seconds」的片段保存为 mp4。
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BufferedFrame:
    timestamp: float
    frame: np.ndarray  # BGR 帧


class RingBuffer:
    """环形帧缓冲（线程安全）。"""

    def __init__(self, max_seconds: float = 30.0, fps: int = 10) -> None:
        self.max_seconds = max_seconds
        self.fps = fps
        self.max_frames = int(max_seconds * fps)
        self._buffer: deque[BufferedFrame] = deque(maxlen=self.max_frames)
        self._lock = threading.Lock()

    def append(self, frame: np.ndarray) -> None:
        """追加一帧。"""
        with self._lock:
            self._buffer.append(BufferedFrame(time.monotonic(), frame.copy()))

    def snapshot(self) -> list[BufferedFrame]:
        """取当前缓冲的快照（线程安全）。"""
        with self._lock:
            return list(self._buffer)

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()


class ClipRecorder:
    """事件片段录制器：触发警报时保存前后N秒视频。"""

    def __init__(
        self,
        output_dir: str = "clips",
        pre_seconds: float = 30.0,
        post_seconds: float = 30.0,
        fps: int = 10,
        resolution: tuple[int, int] = (640, 480),
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pre_seconds = pre_seconds
        self.post_seconds = post_seconds
        self.fps = fps
        self.resolution = resolution
        self._recording = False
        self._post_frames: list[BufferedFrame] = []
        self._lock = threading.Lock()

    def trigger(self, clip_type: str) -> None:
        """触发警报，开始录制后录片段。"""
        with self._lock:
            self._recording = True
            self._post_frames.clear()
        logger.info("开始录制事件片段：%s", clip_type)

    def append_post_frame(self, frame: np.ndarray) -> None:
        """主循环里每帧调用，后录阶段的帧攒起来。"""
        if not self._recording:
            return

        with self._lock:
            self._post_frames.append(BufferedFrame(time.monotonic(), frame.copy()))

            # 后录够了，保存
            if len(self._post_frames) >= int(self.post_seconds * self.fps):
                self._recording = False
                self._save_clip(clip_type="unknown")  # 类型在trigger时传，简化处理

    def save(self, pre_frames: list[BufferedFrame], clip_type: str) -> str:
        """保存完整片段：前录（环形缓冲里的）+ 后录（攒的）。"""
        with self._lock:
            post_frames = list(self._post_frames)
            self._recording = False
            self._post_frames.clear()

        all_frames = pre_frames + post_frames
        if len(all_frames) < 10:
            logger.warning("片段太短，跳过保存")
            return ""

        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{clip_type}_{timestamp_str}.mp4"
        filepath = self.output_dir / filename

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(filepath), fourcc, self.fps, self.resolution)

        for bf in all_frames:
            frame = bf.frame
            # 确保尺寸一致
            if frame.shape[1] != self.resolution[0] or frame.shape[0] != self.resolution[1]:
                frame = cv2.resize(frame, self.resolution)
            writer.write(frame)

        writer.release()
        logger.info("片段已保存：%s（%d 帧）", filepath, len(all_frames))
        return str(filepath)

    def _save_clip(self, clip_type: str) -> None:
        """内部方法，简化。"""
        pass
