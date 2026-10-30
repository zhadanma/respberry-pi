"""A-1 跌倒判定状态机。

判定逻辑：
1. 人体框宽高比 > RATIO_THRESHOLD（横宽）
2. 头部 Y 坐标没有明显升高（容差 HEAD_Y_TOLERANCE）
3. 持续 FALL_CONFIRM_SECONDS 秒未恢复（否则只是弯腰、坐下）
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from ..detect.vision import PersonPose

logger = logging.getLogger(__name__)

# 配置常量（可被外部覆盖）
DEFAULT_RATIO_THRESHOLD = 1.8       # 宽高比超过此值算"横宽"（正常坐姿约1.0~1.5）
DEFAULT_RATIO_NORMAL = 2.0         # 超过此值画红框
DEFAULT_HEAD_Y_TOLERANCE = 20.0    # 头部 Y 坐标容差（像素）
DEFAULT_CONFIRM_SECONDS = 5        # 持续多久确认跌倒
DEFAULT_CONFIDENCE_THRESHOLD = 0.6 # 置信度阈值


@dataclass
class FallState:
    is_falling: bool = False
    fall_start_time: float = 0.0
    last_head_y: float = 0.0
    fall_confidence: float = 0.0


class FallDetector:
    def __init__(
        self,
        fall_confirm_seconds: int = DEFAULT_CONFIRM_SECONDS,
        fall_confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        ratio_threshold: float = DEFAULT_RATIO_THRESHOLD,
        head_y_tolerance: float = DEFAULT_HEAD_Y_TOLERANCE,
    ) -> None:
        self.fall_confirm_seconds = fall_confirm_seconds
        self.fall_confidence_threshold = fall_confidence_threshold
        self.ratio_threshold = ratio_threshold
        self.head_y_tolerance = head_y_tolerance
        self.state = FallState()

    def update(self, persons: list[PersonPose], timestamp: float | None = None) -> bool:
        now = timestamp if timestamp is not None else time.monotonic()

        if not persons:
            self._reset()
            return False

        person = persons[0]
        head_y = person.head_y
        ratio = person.bbox_ratio

        # 计算跌倒置信度：宽高比越大置信度越高（1.5~2.5 区间线性增长）
        ratio_score = max(0.0, min(1.0, (ratio - 1.5) / 1.0))
        confidence = ratio_score * person.confidence

        # 疑似跌倒：横宽 + 头部没有明显升高
        if ratio > self.ratio_threshold and head_y > self.state.last_head_y - self.head_y_tolerance:
            if not self.state.is_falling:
                self.state.is_falling = True
                self.state.fall_start_time = now
                logger.info("疑似跌倒开始：ratio=%.2f, head_y=%.1f", ratio, head_y)

            self.state.fall_confidence = confidence

            if now - self.state.fall_start_time >= self.fall_confirm_seconds:
                logger.warning(
                    "确认跌倒！持续 %.1f 秒，置信度 %.2f",
                    now - self.state.fall_start_time, confidence,
                )
                self.state.is_falling = False
                return True
        else:
            if self.state.is_falling:
                logger.info("疑似跌倒恢复：ratio=%.2f", ratio)
            self._reset()

        self.state.last_head_y = head_y
        return False

    def _reset(self) -> None:
        self.state.is_falling = False
        self.state.fall_start_time = 0.0
        self.state.fall_confidence = 0.0

    @property
    def current_confidence(self) -> float:
        return self.state.fall_confidence
