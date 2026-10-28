"""主调度：串联采集、推流、上报与配置轮询。

阶段一使用假数据：按周期上报「系统运行正常」，不接入任何模型。
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

import cv2

from .capture import create_camera
from .comm import PcClient
from .config import ConfigManager, Settings
from .stream import FrameHub, create_app, start_server

logger = logging.getLogger(__name__)


class MonitorApp:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.config = ConfigManager()
        self.hub = FrameHub()
        self.client = PcClient(
            base_url=settings.pc_base_url,
            token=settings.api_token,
            device_id=settings.device_id,
            timeout=settings.http_timeout_seconds,
        )
        self.camera = create_camera(settings)
        self._stop = threading.Event()
        self._workers: list[threading.Thread] = []

    def run(self) -> None:
        if self.settings.api_token == "change-me":
            logger.warning("API_TOKEN 仍是默认值 change-me，请与 PC 端一起修改")

        self.camera.start()
        app = create_app(self.hub, self.settings.api_token)
        server = start_server(app, self.settings.monitor_host, self.settings.monitor_port)

        logger.info("监控端启动：device_id=%s PC=%s", self.settings.device_id, self.settings.pc_base_url)
        logger.info("当前配置：%s", self.config.describe())

        self._spawn(self._config_loop, "config-poller")
        self._spawn(self._report_loop, "reporter")
        self._spawn(server.serve_forever, "mjpeg-server")

        try:
            self._frame_loop()
        except KeyboardInterrupt:
            logger.info("收到中断，正在退出…")
        finally:
            self._shutdown(server)

    def send_demo_alert(self) -> bool:
        logger.info("发送一条演示警报…")
        return self.client.send_report("normal", "演示前的连通性检查") and self.client.send_alert(
            alert_type="fall",
            confidence=0.88,
            message="演示警报：检测到跌倒（阶段一假数据）",
        )

    def _frame_loop(self) -> None:
        interval = 1.0 / self.settings.video_fps
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.settings.video_jpeg_quality]
        frames = 0
        last_log = time.monotonic()
        while not self._stop.is_set():
            started = time.monotonic()
            frame = self.camera.read()
            if frame is None:
                logger.warning("取帧失败，0.5 秒后重试")
                self._stop.wait(0.5)
                continue
            ok, buffer = cv2.imencode(".jpg", frame, encode_params)
            if ok:
                self.hub.publish(buffer.tobytes())
                frames += 1
            elapsed = time.monotonic() - started
            self._stop.wait(max(0.0, interval - elapsed))

            now = time.monotonic()
            if now - last_log >= 60:
                logger.info("采集正常：近 %d 秒 %d 帧（目标 %d fps）", int(now - last_log), frames, self.settings.video_fps)
                frames = 0
                last_log = now

    def _report_loop(self) -> None:
        last_sent = 0.0
        while not self._stop.is_set():
            interval = self.config.snapshot().report_interval_seconds
            now = time.monotonic()
            if now - last_sent >= interval:
                if self.client.send_report("normal", "系统运行正常（阶段一假数据）"):
                    logger.info("状态报告已上报（周期 %ss）", interval)
                last_sent = now
            self._stop.wait(0.5)

    def _config_loop(self) -> None:
        while not self._stop.is_set():
            payload = self.client.fetch_config()
            if payload is not None and self.config.apply(payload):
                logger.info("配置已更新：%s", self.config.describe())
            self._stop.wait(self.settings.config_poll_seconds)

    def _spawn(self, target, name: str) -> None:
        thread = threading.Thread(target=target, name=name, daemon=True)
        thread.start()
        self._workers.append(thread)

    def _shutdown(self, server) -> None:
        self._stop.set()
        self.hub.close()
        server.shutdown()
        self.camera.close()
        self.client.close()
        for thread in self._workers:
            thread.join(timeout=2.0)
        logger.info("监控端已退出（%s）", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
