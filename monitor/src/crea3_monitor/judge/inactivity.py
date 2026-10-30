"""A-2 非睡眠时段长时间静止判定。

判定逻辑：
1. 对当前帧和上一帧都置信度 > 0.3 的对应关键点计算位移
2. 平均位移低于阈值 → 累计静止时间
3. 静止时间超过 inactivity_minutes → 触发警报
4. 睡眠时段内不判定

state 加 threading.Lock 保护，为多线程集成做准备。
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field

import numpy as np
from datetime import datetime

from ..detect.vision import PersonPose

logger = logging.getLogger(__name__)

# 配置常量
DEFAULT_INACTIVITY_MINUTES = 30
DEFAULT_SLEEP_START = "22:00"
DEFAULT_SLEEP_END = "07:00"
DEFAULT_DISPLACEMENT_THRESHOLD = 15.0  # 像素
DEFAULT_KPT_CONFIDENCE = 0.3  # 只统计置信度高于此值的关键点


@dataclass
class InactivityState:
    is_inactive: bool = False
    inactive_start_time: float = 0.0
    last_keypoints: np.ndarray | None = None  # shape (17, 3)，与当前帧结构对齐
    displacement: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


class InactivityDetector:
    def __init__(
        self,
        inactivity_minutes: int = DEFAULT_INACTIVITY_MINUTES,
        sleep_start: str = DEFAULT_SLEEP_START,
        sleep_end: str = DEFAULT_SLEEP_END,
        displacement_threshold: float = DEFAULT_DISPLACEMENT_THRESHOLD,
        kpt_confidence: float = DEFAULT_KPT_CONFIDENCE,
    ) -> None:
        self.inactivity_seconds = inactivity_minutes * 60
        self.sleep_start = sleep_start
        self.sleep_end = sleep_end
        self.displacement_threshold = displacement_threshold
        self.kpt_confidence = kpt_confidence
        self.state = InactivityState()

    def update(self, persons: list[PersonPose], now: datetime | None = None) -> bool:
        """每帧更新，返回是否触发静止警报。触发后自动重置。"""
        if now is None:
            now = datetime.now()

        # 睡眠时段直接重置
        if self._is_sleep_time(now):
            with self.state.lock:
                self._reset_locked()
            return False

        if not persons:
            return False

        person = persons[0]
        current_kpts = person.keypoints  # shape (17, 3): x, y, conf

        with self.state.lock:
            if self.state.last_keypoints is None:
                self.state.last_keypoints = current_kpts.copy()
                return False

            prev_kpts = self.state.last_keypoints

            # 逐点对比：只有当前帧和上一帧该点置信度都 > 阈值才计算位移
            total_disp = 0.0
            valid_count = 0
            for i in range(current_kpts.shape[0]):
                cur_conf = current_kpts[i][2]
                prev_conf = prev_kpts[i][2]
                if cur_conf > self.kpt_confidence and prev_conf > self.kpt_confidence:
                    dx = current_kpts[i][0] - prev_kpts[i][0]
                    dy = current_kpts[i][1] - prev_kpts[i][1]
                    total_disp += (dx * dx + dy * dy) ** 0.5
                    valid_count += 1

            # 有效点太少（可能遮挡严重），不做判定，保持上次状态
            if valid_count < 3:
                self.state.last_keypoints = current_kpts.copy()
                return False

            displacement = total_disp / valid_count
            self.state.displacement = displacement
            self.state.last_keypoints = current_kpts.copy()

            if displacement < self.displacement_threshold:
                if not self.state.is_inactive:
                    self.state.is_inactive = True
                    self.state.inactive_start_time = time.monotonic()
                    logger.info("开始计时静止：阈值 %.0f 秒", self.inactivity_seconds)

                elapsed = time.monotonic() - self.state.inactive_start_time
                if elapsed >= self.inactivity_seconds:
                    logger.warning("确认长时间静止！已静止 %.1f 秒", elapsed)
                    self._reset_locked()
                    return True
            else:
                if self.state.is_inactive:
                    logger.info("静止恢复：位移 %.1f 像素", displacement)
                self._reset_locked()

        return False

    def _is_sleep_time(self, now: datetime) -> bool:
        current_minutes = now.hour * 60 + now.minute
        start_h, start_m = map(int, self.sleep_start.split(":"))
        end_h, end_m = map(int, self.sleep_end.split(":"))
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

        if start_minutes <= end_minutes:
            return current_minutes < start_minutes or current_minutes >= end_minutes
        else:
            return current_minutes >= start_minutes or current_minutes < end_minutes

    def _reset_locked(self) -> None:
        """调用方必须持有 state.lock。"""
        self.state.is_inactive = False
        self.state.inactive_start_time = 0.0
        self.state.displacement = 0.0

    @property
    def inactive_seconds_elapsed(self) -> float:
        with self.state.lock:
            if not self.state.is_inactive:
                return 0.0
            return time.monotonic() - self.state.inactive_start_time
