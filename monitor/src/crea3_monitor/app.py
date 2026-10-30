"""主调度：串联所有模块。

线程分工：
- 主线程：视频采集 + 视觉推理 + MJPEG推流
- 音频线程：麦克风采块 → 音频特征提取 → 呼救/异常声判定
- 配置轮询线程：定期拉取PC配置
- 状态上报线程：按周期发状态报告
- 离线队列重试线程：断网时补传失败的report/alert
- Flask线程：MJPEG视频推流
- WebSocket线程：音频PCM推流
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from datetime import datetime

import cv2
import numpy as np

from .capture import create_camera, create_microphone
from .comm import PcClient
from .comm.offline_queue import OfflineQueue
from .comm.retry_worker import RetryWorker
from .config import ConfigManager, Settings
from .detect.vision import VisionDetector
from .detect.audio import AudioDetector
from .judge.fall import FallDetector
from .judge.inactivity import InactivityDetector
from .judge.scream import ScreamDetector
from .judge.noise import NoiseDetector
from .mail.notifier import MailNotifier, MailConfig
from .stream.stream_server import StreamService

logger = logging.getLogger(__name__)


class MonitorApp:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.config = ConfigManager()

        # 离线队列（断网缓冲）
        self.offline_queue = OfflineQueue(db_path=settings.offline_queue_db)

        # PC通信客户端（带离线队列）
        self.client = PcClient(
            base_url=settings.pc_base_url,
            token=settings.api_token,
            device_id=settings.device_id,
            timeout=settings.http_timeout_seconds,
            offline_queue=self.offline_queue,
        )

        # 重试线程
        self.retry_worker = RetryWorker(
            queue=self.offline_queue,
            base_url=settings.pc_base_url,
            token=settings.api_token,
        )

        # 推流服务
        self.stream = StreamService(
            token=settings.api_token,
            host=settings.monitor_host,
            video_port=settings.monitor_port,
            audio_ws_port=settings.audio_ws_port,
        )

        # 采集设备
        self.camera = create_camera(settings)
        self.microphone = create_microphone(settings)

        # 视觉检测
        self.vision = VisionDetector(model_name="yolov8n-pose.pt", device="cpu")
        self.fall_detector = FallDetector()
        self.inactivity_detector = InactivityDetector()
        self._detect_interval = 3  # 每3帧推理一次（CPU限制）
        self._frame_count = 0

        # 音频检测
        self.audio_detector = AudioDetector(sample_rate=settings.audio_sample_rate)
        self.scream_detector = ScreamDetector()
        self.noise_detector = NoiseDetector()

        # 邮件通知
        mail_config = MailConfig(
            smtp_host=settings.smtp_host,
            smtp_port=settings.smtp_port,
            sender_email=settings.sender_email,
            sender_password=settings.sender_password,
            receiver_emails=settings.receiver_emails,
        )
        self.notifier = MailNotifier(mail_config)

        # 控制
        self._stop = threading.Event()
        self._workers: list[threading.Thread] = []

    def run(self) -> None:
        if self.settings.api_token == "change-me":
            logger.warning("API_TOKEN 仍是默认值 change-me，请与 PC 端一起修改")

        # 启动设备
        self.camera.start()
        self.microphone.start()

        # 启动推流服务
        self.stream.start()

        logger.info("=" * 60)
        logger.info("监控端启动：device_id=%s", self.settings.device_id)
        logger.info("PC端：%s", self.settings.pc_base_url)
        logger.info("视频流：http://%s:%d/stream/video",
                     self.settings.monitor_host, self.settings.monitor_port)
        logger.info("音频流：ws://%s:%d/stream/audio",
                     self.settings.monitor_host, self.settings.audio_ws_port)
        logger.info("当前配置：%s", self.config.describe())
        stats = self.offline_queue.stats()
        logger.info("离线队列：待处理=%d 已发送=%d 失败=%d",
                     stats["pending"], stats["sent"], stats["failed"])
        logger.info("=" * 60)

        # 启动后台线程
        self._spawn(self._config_loop, "config-poller")
        self._spawn(self._report_loop, "reporter")
        self._spawn(self._audio_loop, "audio-processor")
        self.retry_worker.start()

        try:
            self._frame_loop()
        except KeyboardInterrupt:
            logger.info("收到中断，正在退出…")
        finally:
            self._shutdown()

    def send_demo_alert(self) -> bool:
        """发送一条演示警报（启动时连通性检查）。"""
        logger.info("发送演示警报…")
        ok1 = self.client.send_report("normal", "监控端启动，连通性检查")
        ok2 = self.client.send_alert(
            alert_type="fall",
            confidence=0.88,
            message="演示警报：检测到跌倒（启动自检）",
        )
        return ok1 and ok2

    # === 视频主循环 ===

    def _frame_loop(self) -> None:
        interval = 1.0 / self.settings.video_fps
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.settings.video_jpeg_quality]
        frames = 0
        last_log = time.monotonic()
        last_persons_count = 0

        while not self._stop.is_set():
            started = time.monotonic()
            frame = self.camera.read()
            if frame is None:
                logger.warning("取帧失败，0.5秒后重试")
                self._stop.wait(0.5)
                continue

            self._frame_count += 1

            # 每 N 帧做一次视觉推理
            if self._frame_count % self._detect_interval == 0:
                persons = self.vision.detect(frame)
                last_persons_count = len(persons)

                cfg = self.config.snapshot()

                # 更新判定器参数
                self.fall_detector.fall_confirm_seconds = cfg.fall_confirm_seconds
                self.fall_detector.fall_confidence_threshold = cfg.fall_confidence
                self.inactivity_detector.inactivity_seconds = cfg.inactivity_minutes * 60
                self.inactivity_detector.sleep_start = cfg.sleep_start
                self.inactivity_detector.sleep_end = cfg.sleep_end

                # 跌倒检测
                if self.fall_detector.update(persons):
                    conf = self.fall_detector.current_confidence
                    self._trigger_alert(
                        alert_type="fall",
                        confidence=conf,
                        message=f"检测到跌倒，持续 {cfg.fall_confirm_seconds} 秒未起身",
                    )

                # 长时间静止检测
                if self.inactivity_detector.update(persons):
                    self._trigger_alert(
                        alert_type="inactivity",
                        confidence=0.7,
                        message=f"非睡眠时段静止超过 {cfg.inactivity_minutes} 分钟",
                    )

                # 画检测框（调试用）
                frame = self.vision.draw_overlay(frame, persons)

            # 推流帧
            ok, buffer = cv2.imencode(".jpg", frame, encode_params)
            if ok:
                self.stream.frame_hub.publish(buffer.tobytes())
                frames += 1

            elapsed = time.monotonic() - started
            self._stop.wait(max(0.0, interval - elapsed))

            now = time.monotonic()
            if now - last_log >= 60:
                logger.info(
                    "采集正常：%d秒%d帧（目标%d fps），检测到人%d个",
                    int(now - last_log), frames, self.settings.video_fps, last_persons_count,
                )
                frames = 0
                last_log = now

    # === 音频处理线程 ===

    def _audio_loop(self) -> None:
        """音频采集 + 特征提取 + 判定 + 推流。"""
        while not self._stop.is_set():
            block = self.microphone.read(timeout=1.0)
            if block is None:
                continue

            # 1. 音频推流（WS）
            self.stream.audio_hub.publish(block)

            # 2. 提取特征
            features = self.audio_detector.extract(block)

            # 3. 呼救声判定
            if self.scream_detector.update(features):
                self._trigger_alert(
                    alert_type="cry",
                    confidence=0.8,
                    message="检测到呼救/尖叫声",
                )

            # 4. 异常声响判定
            if self.noise_detector.update(features):
                self._trigger_alert(
                    alert_type="abnormal_sound",
                    confidence=0.75,
                    message=f"检测到异常声响（RMS={features.rms:.3f}）",
                )

    # === 警报触发统一入口 ===

    def _trigger_alert(self, alert_type: str, confidence: float, message: str) -> None:
        """触发警报：发PC端 + 发邮件。"""
        logger.warning("触发警报：%s - %s", alert_type, message)

        # 1. 发给PC端（失败自动入队）
        self.client.send_alert(
            alert_type=alert_type,
            confidence=confidence,
            message=message,
        )

        # 2. 发邮件（异步，不阻塞）
        self.notifier.send_alert(
            device_id=self.settings.device_id,
            alert_type=alert_type,
            confidence=confidence,
            message=message,
            has_clip=False,  # 片段由PC端Java负责保存
        )

    # === 状态上报线程 ===

    def _report_loop(self) -> None:
        last_sent = 0.0
        while not self._stop.is_set():
            interval = self.config.snapshot().report_interval_seconds
            now = time.monotonic()
            if now - last_sent >= interval:
                if self.client.send_report("normal", "系统运行正常"):
                    logger.info("状态报告已上报（周期%ds）", interval)
                last_sent = now
            self._stop.wait(0.5)

    # === 配置轮询线程 ===

    def _config_loop(self) -> None:
        while not self._stop.is_set():
            payload = self.client.fetch_config()
            if payload is not None and self.config.apply(payload):
                logger.info("配置已更新：%s", self.config.describe())
            self._stop.wait(self.settings.config_poll_seconds)

    # === 工具 ===

    def _spawn(self, target, name: str) -> None:
        thread = threading.Thread(target=target, name=name, daemon=True)
        thread.start()
        self._workers.append(thread)

    def _shutdown(self) -> None:
        self._stop.set()
        self.stream.shutdown()
        self.retry_worker.stop()
        self.camera.close()
        self.microphone.close()
        self.notifier.shutdown()
        self.client.close()
        for thread in self._workers:
            thread.join(timeout=2.0)
        logger.info("监控端已退出（%s）", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
