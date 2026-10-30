"""后台重试线程：定期扫描离线队列，补传失败的 report 和 alert。

特点：
- 每 5 秒扫描一次，alert 优先于 report
- 发送前标记为 SENDING，防止多线程重复发
- 发送成功标记 SENT，失败则 retry_count+1 并按退避策略计算下次重试时间
- 启动时自动清理 7 天前已 SENT 的记录
"""

from __future__ import annotations

import logging
import threading
import time

import requests

from .offline_queue import OfflineQueue, QueueItem

logger = logging.getLogger(__name__)


class RetryWorker:
    """离线队列后台重试线程。"""

    def __init__(
        self,
        queue: OfflineQueue,
        base_url: str,
        token: str,
        poll_interval: float = 5.0,
        batch_size: int = 10,
        timeout: float = 5.0,
        cleanup_days: int = 7,
    ) -> None:
        self.queue = queue
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self.timeout = timeout
        self.cleanup_days = cleanup_days

        self._running = False
        self._thread: threading.Thread | None = None
        self._cleanup_interval = 3600  # 每小时清理一次
        self._last_cleanup = 0.0

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, name="queue-retry", daemon=True,
        )
        self._thread.start()
        logger.info("离线队列重试线程已启动（%.0f秒扫描一次）", self.poll_interval)

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _loop(self) -> None:
        while self._running:
            try:
                self._process_batch()
                self._maybe_cleanup()
            except Exception as exc:
                logger.error("重试线程异常：%s", exc)
            time.sleep(self.poll_interval)

    def _process_batch(self) -> None:
        items = self.queue.get_retryable(limit=self.batch_size)
        if not items:
            return

        logger.info("处理 %d 条离线队列待补传", len(items))

        for item in items:
            if not self._running:
                break
            self._try_send(item)

    def _try_send(self, item: QueueItem) -> None:
        """尝试发送单条，成功置SENT，失败计数+1。"""
        self.queue.mark_sending(item.id)

        url = f"{self.base_url}{item.endpoint}"
        headers = {"X-Auth-Token": self.token}

        try:
            resp = requests.post(url, json=item.payload, headers=headers, timeout=self.timeout)
            if resp.status_code == 200 and resp.json().get("ok") is True:
                self.queue.mark_sent(item.id)
                logger.info("补传成功：%s (id=%d)", item.endpoint, item.id)
            else:
                logger.warning(
                    "补传失败：%s (id=%d) HTTP %s %s",
                    item.endpoint, item.id, resp.status_code, resp.text[:200],
                )
                self.queue.mark_failed_after_retry(item.id)
        except requests.RequestException as exc:
            logger.warning("补传失败：%s (id=%d) 网络错误: %s", item.endpoint, item.id, exc)
            self.queue.mark_failed_after_retry(item.id)
        except Exception as exc:
            logger.error("补传异常：%s (id=%d) %s", item.endpoint, item.id, exc)
            self.queue.mark_failed_after_retry(item.id)

    def _maybe_cleanup(self) -> None:
        now = time.time()
        if now - self._last_cleanup >= self._cleanup_interval:
            deleted = self.queue.cleanup_old(days=self.cleanup_days)
            if deleted > 0:
                logger.info("清理了 %d 条已发送超过 %d 天的队列记录", deleted, self.cleanup_days)
            self._last_cleanup = now
