"""本地缓冲模块：断网时不丢数据。

- 视频环形缓冲：最近N秒帧，触发警报时保存前后片段
- 音频环形缓冲：最近N秒音频块，和视频对齐保存
- SQLite 队列：文本数据（报告/警报）断网时暂存，恢复后补传
"""

from .video_ring import RingBuffer, ClipRecorder
from .audio_ring import AudioRingBuffer, save_audio_wav

__all__ = ["RingBuffer", "ClipRecorder", "AudioRingBuffer", "save_audio_wav"]
