"""采集模块：摄像头取帧、麦克风取音频块。

对外提供统一接口，隔离两种实现：
- 开发期（PC）：OpenCV VideoCapture 读 USB / 内置摄像头
- 部署期（树莓派）：picamera2 读 MIPI CSI 摄像头
迁移时只替换底层实现，上层逻辑不变。
"""

from .base import CameraSource, MicrophoneSource
from .factory import create_camera, create_microphone

__all__ = ["CameraSource", "MicrophoneSource", "create_camera", "create_microphone"]
