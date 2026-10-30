"""推流模块：持续向 PC 推送音视频。

- 视频：MJPEG over HTTP（/stream/video）
- 音频：WebSocket（/stream/audio）
- 健康检查：/health
"""

from .stream_server import FrameHub, AudioHub, StreamService

__all__ = ["FrameHub", "AudioHub", "StreamService"]
