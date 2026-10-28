"""采集设备工厂：按配置选择后端。迁移树莓派时在此新增 picamera2。"""

from __future__ import annotations

from ..config.settings import Settings
from .base import CameraSource, MicrophoneSource
from .microphone import SoundDeviceMicrophone
from .opencv_camera import OpenCVCamera


def create_camera(settings: Settings) -> CameraSource:
    if settings.camera_backend == "opencv":
        return OpenCVCamera(
            index=settings.camera_index,
            width=settings.video_width,
            height=settings.video_height,
            fps=settings.video_fps,
        )
    if settings.camera_backend == "picamera2":
        raise NotImplementedError("picamera2 后端在 P7 迁移阶段实现")
    raise ValueError(f"未知的 CAMERA_BACKEND：{settings.camera_backend}")


def create_microphone(settings: Settings) -> MicrophoneSource:
    return SoundDeviceMicrophone(
        sample_rate=settings.audio_sample_rate,
        device=settings.audio_device,
    )
