"""监控端启动配置：默认值 < .env < 环境变量。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

MONITOR_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = MONITOR_DIR / ".env"

DEFAULTS: dict[str, str] = {
    "DEVICE_ID": "monitor-01",
    "PC_BASE_URL": "http://127.0.0.1:8080",
    "API_TOKEN": "change-me",
    "CAMERA_BACKEND": "opencv",
    "CAMERA_INDEX": "0",
    "VIDEO_WIDTH": "640",
    "VIDEO_HEIGHT": "480",
    "VIDEO_FPS": "10",
    "VIDEO_JPEG_QUALITY": "70",
    "MONITOR_HOST": "0.0.0.0",
    "MONITOR_PORT": "8000",
    "CONFIG_POLL_SECONDS": "10",
    "HTTP_TIMEOUT_SECONDS": "5",
    "AUDIO_SAMPLE_RATE": "16000",
    "AUDIO_DEVICE": "",
}


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


@dataclass(frozen=True)
class Settings:
    device_id: str
    pc_base_url: str
    api_token: str
    camera_backend: str
    camera_index: int
    video_width: int
    video_height: int
    video_fps: int
    video_jpeg_quality: int
    monitor_host: str
    monitor_port: int
    config_poll_seconds: float
    http_timeout_seconds: float
    audio_sample_rate: int
    audio_device: int | None


def load_settings() -> Settings:
    file_values = _load_env_file(ENV_FILE)

    def get(key: str) -> str:
        return os.environ.get(key, file_values.get(key, DEFAULTS[key])).strip()

    device = get("AUDIO_DEVICE")
    return Settings(
        device_id=get("DEVICE_ID"),
        pc_base_url=get("PC_BASE_URL").rstrip("/"),
        api_token=get("API_TOKEN"),
        camera_backend=get("CAMERA_BACKEND").lower(),
        camera_index=int(get("CAMERA_INDEX")),
        video_width=int(get("VIDEO_WIDTH")),
        video_height=int(get("VIDEO_HEIGHT")),
        video_fps=max(1, int(get("VIDEO_FPS"))),
        video_jpeg_quality=min(100, max(1, int(get("VIDEO_JPEG_QUALITY")))),
        monitor_host=get("MONITOR_HOST"),
        monitor_port=int(get("MONITOR_PORT")),
        config_poll_seconds=max(1.0, float(get("CONFIG_POLL_SECONDS"))),
        http_timeout_seconds=max(1.0, float(get("HTTP_TIMEOUT_SECONDS"))),
        audio_sample_rate=int(get("AUDIO_SAMPLE_RATE")),
        audio_device=int(device) if device else None,
    )
