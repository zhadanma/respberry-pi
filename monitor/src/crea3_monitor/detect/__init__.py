"""检测模块：模型推理，只负责输出结果，不做业务判断。

- 视觉：YOLOv8n-pose → 人体框 + 17 个关键点
- 音频：RMS 能量 + 频谱质心（轻量版，后续升级 YAMNet）
"""

from .vision import VisionDetector, PersonPose
from .audio import AudioDetector, AudioFeatures

__all__ = ["VisionDetector", "PersonPose", "AudioDetector", "AudioFeatures"]
