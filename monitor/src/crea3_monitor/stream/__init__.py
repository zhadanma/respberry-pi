"""推流模块：持续向 PC 推送音视频。

视频走 MJPEG over HTTP，音频走 WebSocket。复用采集到的帧，避免重复取流。
"""

from .hub import FrameHub
from .mjpeg_server import create_app, start_server

__all__ = ["FrameHub", "create_app", "start_server"]
