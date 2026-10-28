"""最新帧中枢：采集线程写入，所有预览客户端各自读取，互不阻塞。"""

from __future__ import annotations

import threading
from typing import Iterator


class FrameHub:
    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._jpeg: bytes | None = None
        self._sequence = 0
        self._closed = False

    def publish(self, jpeg: bytes) -> None:
        with self._condition:
            self._jpeg = jpeg
            self._sequence += 1
            self._condition.notify_all()

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()

    def wait_frame(self, last_sequence: int, timeout: float = 2.0) -> tuple[int, bytes] | None:
        with self._condition:
            if self._sequence == last_sequence and not self._closed:
                self._condition.wait(timeout)
            if self._closed or self._jpeg is None or self._sequence == last_sequence:
                return None
            return self._sequence, self._jpeg

    def stream(self) -> Iterator[bytes]:
        """按产出顺序逐帧生成 JPEG，供 multipart/x-mixed-replace 响应使用。"""
        sequence = 0
        while True:
            frame = self.wait_frame(sequence)
            if frame is None:
                if self._closed:
                    return
                continue
            sequence, jpeg = frame
            yield jpeg
