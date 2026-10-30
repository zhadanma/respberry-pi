"""YOLOv8n-pose 测试脚本。

用法：
1. 图片测试：python test_vision.py --image test.jpg
2. 摄像头实时测试：python test_vision.py --camera

注意：本脚本仅用于调试，正式环境阈值从配置读取。
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import cv2

# 兼容 src/ 布局和平铺布局两种 import 方式
sys.path.insert(0, str(Path(__file__).parent / "src"))

from crea3_monitor.detect.vision import VisionDetector
from crea3_monitor.judge.fall import FallDetector
from crea3_monitor.judge.inactivity import InactivityDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("test_vision")


def test_image(image_path: str) -> None:
    logger.info("加载图片：%s", image_path)
    frame = cv2.imread(image_path)
    if frame is None:
        logger.error("无法读取图片：%s", image_path)
        return

    detector = VisionDetector()
    persons = detector.detect(frame)

    logger.info("检测到 %d 个人", len(persons))
    for i, p in enumerate(persons):
        logger.info(
            "  人 #%d: bbox=%s, conf=%.2f, ratio=%.2f, head_y=%.1f",
            i, p.bbox, p.confidence, p.bbox_ratio, p.head_y,
        )

    output = detector.draw_overlay(frame, persons)
    out_path = str(Path(image_path).with_name(Path(image_path).stem + "_result.jpg"))
    cv2.imwrite(out_path, output)
    logger.info("结果已保存：%s", out_path)


def test_camera(
    fall_confirm_seconds: int = 5,
    inactivity_minutes: int = 30,
) -> None:
    """摄像头实时测试。阈值从参数传入。"""
    logger.info(
        "摄像头实时测试（q 退出）：跌倒确认 %ds，静止 %dmin",
        fall_confirm_seconds, inactivity_minutes,
    )

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    detector = VisionDetector()
    fall = FallDetector(fall_confirm_seconds=fall_confirm_seconds)
    inactive = InactivityDetector(inactivity_minutes=inactivity_minutes)

    frame_count = 0
    last_fall = False
    last_inactive = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        persons = []

        if frame_count % 3 == 0:
            persons = detector.detect(frame)

            if fall.update(persons):
                last_fall = True
                logger.warning("FALL TRIGGERED! conf=%.2f", fall.current_confidence)

            if inactive.update(persons):
                last_inactive = True
                logger.warning("INACTIVITY TRIGGERED!")

        output = detector.draw_overlay(frame, persons)

        # 状态栏（英文，OpenCV 不支持中文）
        status = "Normal"
        color = (0, 255, 0)
        if last_fall:
            status = "FALL TRIGGERED!"
            color = (0, 0, 255)
            last_fall = False
        elif last_inactive:
            status = "INACTIVITY TRIGGERED!"
            color = (0, 0, 255)
            last_inactive = False
        elif fall.state.is_falling:
            status = f"Suspected fall... {time.monotonic() - fall.state.fall_start_time:.1f}s"
            color = (0, 255, 255)
        elif inactive.state.is_inactive:
            status = f"Inactivity... {inactive.inactive_seconds_elapsed:.0f}s"
            color = (0, 255, 255)

        cv2.putText(output, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(
            output, f"People: {len(persons)}", (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1,
        )

        cv2.imshow("Vision Test (q to quit)", output)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    logger.info("测试结束")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLOv8n-pose 测试")
    parser.add_argument("--image", type=str, help="测试图片路径")
    parser.add_argument("--camera", action="store_true", help="摄像头实时测试")
    parser.add_argument("--fall-seconds", type=int, default=5, help="跌倒确认秒数（默认5）")
    parser.add_argument("--inactive-minutes", type=int, default=30, help="静止分钟数（默认30）")
    args = parser.parse_args()

    if args.image:
        test_image(args.image)
    elif args.camera:
        test_camera(
            fall_confirm_seconds=args.fall_seconds,
            inactivity_minutes=args.inactive_minutes,
        )
    else:
        parser.print_help()
