"""与 PC 端通信：所有请求由监控端主动发起。"""

from __future__ import annotations

import logging
from datetime import datetime

import requests

logger = logging.getLogger(__name__)


class PcClient:
    def __init__(self, base_url: str, token: str, device_id: str, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.device_id = device_id
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
        return self._post("/api/report", payload)

    def send_alert(self, alert_type: str, confidence: float, message: str) -> bool:
        payload = {
            "device_id": self.device_id,
            "timestamp": _now(),
            "type": alert_type,
            "confidence": round(float(confidence), 3),
            "message": message,
        }
        return self._post("/api/alert", payload)

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

    def _post(self, path: str, payload: dict) -> bool:
        url = f"{self.base_url}{path}"
        try:
            response = self._session.post(url, json=payload, timeout=self._timeout)
        except requests.RequestException as exc:
            logger.warning("上报 %s 失败：%s", path, exc)
            return False
        if response.status_code != 200:
            logger.warning("上报 %s 失败：HTTP %s %s", path, response.status_code, response.text[:200])
            return False
        return True

    def _log_config_failure(self, message: str) -> None:
        self._config_failures += 1
        # 首次失败立即告警，之后每 10 次提示一次，避免刷屏
        if self._config_failures == 1 or self._config_failures % 10 == 0:
            logger.warning("%s（连续失败 %s 次，沿用最近一次有效配置）", message, self._config_failures)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
