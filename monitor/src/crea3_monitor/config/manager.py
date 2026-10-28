"""运行期配置：以 PC 下发为准，拉取失败时沿用最近一次有效值（R-009）。"""

from __future__ import annotations

import logging
import threading
from dataclasses import asdict, dataclass, replace

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeConfig:
    version: int = 0
    sleep_start: str = "22:00"
    sleep_end: str = "07:00"
    inactivity_minutes: int = 30
    fall_confirm_seconds: int = 5
    report_interval_seconds: int = 3600
    fall_confidence: float = 0.6
    sound_confidence: float = 0.5
    clip_pre_seconds: int = 30
    clip_post_seconds: int = 30
    clip_retention_days: int = 30


_INT_FIELDS = {
    "inactivity_minutes": (1, 24 * 60),
    "fall_confirm_seconds": (1, 600),
    "report_interval_seconds": (1, 24 * 3600),
    "clip_pre_seconds": (0, 600),
    "clip_post_seconds": (0, 600),
    "clip_retention_days": (1, 3650),
}
_FLOAT_FIELDS = {
    "fall_confidence": (0.0, 1.0),
    "sound_confidence": (0.0, 1.0),
}
_TIME_FIELDS = ("sleep_start", "sleep_end")


class ConfigManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._config = RuntimeConfig()

    def snapshot(self) -> RuntimeConfig:
        with self._lock:
            return self._config

    def apply(self, payload: dict) -> bool:
        """用 PC 下发的配置覆盖当前值，非法字段被忽略。返回是否发生了变化。"""
        with self._lock:
            current = self._config
            updated = current
            for key in _INT_FIELDS:
                if key in payload:
                    low, high = _INT_FIELDS[key]
                    value = _as_int(payload[key])
                    if value is not None and low <= value <= high:
                        updated = replace(updated, **{key: value})
            for key in _FLOAT_FIELDS:
                if key in payload:
                    low, high = _FLOAT_FIELDS[key]
                    value = _as_float(payload[key])
                    if value is not None and low <= value <= high:
                        updated = replace(updated, **{key: value})
            for key in _TIME_FIELDS:
                value = payload.get(key)
                if isinstance(value, str) and _valid_hhmm(value):
                    updated = replace(updated, **{key: value})
            version = _as_int(payload.get("version"))
            if version is None:
                version = current.version
            updated = replace(updated, version=version)
            changed = asdict(updated) != asdict(current)
            self._config = updated
            return changed

    def describe(self) -> str:
        config = self.snapshot()
        return (
            f"v{config.version} 报告周期={config.report_interval_seconds}s "
            f"睡眠时段={config.sleep_start}-{config.sleep_end} "
            f"静止阈值={config.inactivity_minutes}min 前录={config.clip_pre_seconds}s "
            f"后录={config.clip_post_seconds}s"
        )


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _valid_hhmm(value: str) -> bool:
    parts = value.split(":")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        return False
    hour, minute = int(parts[0]), int(parts[1])
    return 0 <= hour <= 23 and 0 <= minute <= 59
