"""与 PC 端通信：所有请求由监控端主动发起。

发送失败时自动写入 OfflineQueue，由后台 RetryWorker 补传。
只缓存 report 和 alert 文本数据，音视频不入队。
"""

from __future__ import annotations

import logging
from datetime import datetime

import requests

from .offline_queue import OfflineQueue

logger = logging.getLogger(__name__)


class PcClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        device_id: str,
        timeout: float = 5.0,
        offline_queue: OfflineQueue | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.device_id = device_id
        self.offline_queue = offline_queue
        self._session = requests.Session()
        self._session.headers.update({"X-Auth-Token": token})
        self._timeout = timeout
        self._config_failures = 0

    def send_report(self, status: str, message: str) -> bool:
        payload = {
            "device_id": self.device_id,
            "timestamp": _now(),
            "status": status,
            "message": message,
        }
        return self._post("/api/report", payload, is_report=True)

    def send_alert(self, alert_type: str, confidence: float, message: str) -> bool:
        payload = {
            "device_id": self.device_id,
            "timestamp": _now(),
            "type": alert_type,
            "confidence": round(float(confidence), 3),
            "message": message,
        }
        return self._post("/api/alert", payload, is_report=False)

    def fetch_config(self) -> dict | None:
        url = f"{self.base_url}/api/config"
        try:
            response = self._session.get(url, timeout=self._timeout)
        except requests.RequestException as exc:
            self._log_config_failure(f"拉取配置失败：{exc}")
            return None
        if response.status_code != 200:
            self._log_config_failure(f"拉取配置失败：HTTP {response.status_code}")
            return None
        if self._config_failures:
            logger.info("配置拉取已恢复（此前连续失败 %s 次）", self._config_failures)
            self._config_failures = 0
        try:
            return response.json()
        except ValueError:
            logger.warning("配置响应不是合法 JSON")
            return None

    def close(self) -> None:
        self._session.close()

    def _post(self, path: str, payload: dict, is_report: bool) -> bool:
        """POST 请求，失败时自动入队离线队列。"""
        url = f"{self.base_url}{path}"
        try:
            response = self._session.post(url, json=payload, timeout=self._timeout)
        except requests.RequestException as exc:
            logger.warning("上报 %s 网络失败：%s", path, exc)
            self._enqueue_if_needed(path, payload, is_report)
            return False

        if response.status_code != 200:
            logger.warning("上报 %s 失败：HTTP %s %s", path, response.status_code, response.text[:200])
            # 4xx 错误（如字段错误）不入队，重试也没用
            if 400 <= response.status_code < 500:
                logger.error("客户端错误 %s，不入队：%s", path, response.text[:200])
                return False
            self._enqueue_if_needed(path, payload, is_report)
            return False

        # 检查响应体 ok 字段
        try:
            body = response.json()
            if body.get("ok") is True:
                return True
            else:
                logger.warning("上报 %s 返回 ok=false：%s", path, body)
                self._enqueue_if_needed(path, payload, is_report)
                return False
        except ValueError:
            logger.warning("上报 %s 响应不是合法 JSON", path)
            return False

    def _enqueue_if_needed(self, path: str, payload: dict, is_report: bool) -> None:
        """如果配置了离线队列，就把失败的请求入队。"""
        if self.offline_queue is None:
            return
        try:
            if is_report:
                self.offline_queue.enqueue_report(payload)
            else:
                self.offline_queue.enqueue_alert(payload)
        except Exception as exc:
            logger.error("入队离线队列失败：%s", exc)

    def _log_config_failure(self, message: str) -> None:
        self._config_failures += 1
        if self._config_failures == 1 or self._config_failures % 10 == 0:
            logger.warning("%s（连续失败 %s 次，沿用最近一次有效配置）", message, self._config_failures)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
