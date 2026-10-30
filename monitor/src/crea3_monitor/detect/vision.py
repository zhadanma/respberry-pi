"""视觉检测：YOLOv8n-pose 推理。

只负责输出人体框 + 17 个关键点，不做业务判定（判定在 judge 模块）。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np
from ultralytics import YOLO

logger = logging.getLogger(__name__)


@dataclass
class PersonPose:
    """一个人的姿态检测结果。"""

    bbox: tuple[float, float, float, float]  # (x1, y1, x2, y2)，像素坐标
    keypoints: np.ndarray  # (17, 3)：x, y, confidence
    confidence: float  # 人体检测置信度

    @property
    def bbox_ratio(self) -> float:
        """人体框宽高比（w / h）。> 1 表示横宽（疑似跌倒）。"""
        x1, y1, x2, y2 = self.bbox
        w = x2 - x1
        h = y2 - y1
        return w / max(h, 1.0)

    @property
    def head_y(self) -> float:
        """头部关键点（鼻子）的 y 坐标，用于判断是否倒地。"""
        # 关键点 0 = 鼻子
        return float(self.keypoints[0][1])

    @property
    def is_person_detected(self) -> bool:
        """是否检测到人体。"""
        return self.confidence > 0.5


class VisionDetector:
    """YOLOv8n-pose 姿态检测器。"""

    def __init__(self, model_name: str = "yolov8n-pose.pt", device: str = "cpu") -> None:
        logger.info("加载视觉模型：%s（device=%s）", model_name, device)
        self.model = YOLO(model_name)
        self.device = device
        self._last_results: list[PersonPose] = []

    def detect(self, frame: np.ndarray) -> list[PersonPose]:
        """对一帧图像做姿态推理，返回所有人的姿态。"""
        # frame 是 BGR（OpenCV 惯例），ultralytics 接受 BGR
        results = self.model(frame, verbose=False, device=self.device)

        persons: list[PersonPose] = []
        for result in results:
            if result.keypoints is None or result.boxes is None:
                continue
            boxes = result.boxes.cpu().numpy()
            kpts = result.keypoints.data.cpu().numpy()

            for i in range(len(boxes)):
                x1, y1, x2, y2 = boxes.xyxy[i]
                conf = float(boxes.conf[i])
                keypoints = kpts[i]  # (17, 3)
                persons.append(
                    PersonPose(
                        bbox=(float(x1), float(y1), float(x2), float(y2)),
                        keypoints=keypoints,
                        confidence=conf,
                    )
                )

        self._last_results = persons
        return persons

    @property
    def last_results(self) -> list[PersonPose]:
        return self._last_results

    def draw_overlay(self, frame: np.ndarray, persons: list[PersonPose]) -> np.ndarray:
        """在帧上画检测框和关键点，用于调试和预览。"""
        output = frame.copy()
        for person in persons:
            x1, y1, x2, y2 = [int(v) for v in person.bbox]
            color = (0, 255, 0) if person.bbox_ratio < 1.5 else (0, 0, 255)
            cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)

            # 画关键点
            for kp in person.keypoints:
                kx, ky, kconf = kp
                if kconf > 0.5:
                    cv2.circle(output, (int(kx), int(ky)), 3, color, -1)

            # 标注宽高比
            cv2.putText(
                output,
                f"ratio={person.bbox_ratio:.2f}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
            )
        return output
