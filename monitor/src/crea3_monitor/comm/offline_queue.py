"""断网离线队列：SQLite 实现。

只缓存 report 和 alert 文本数据，音视频片段不入队（断网即丢，PC端自己负责落盘）。
解决了 SENDING 状态崩溃卡死问题：启动时自动把 SENDING 重置为 PENDING。
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class QueueItem:
    id: int
    type: str          # report / alert
    endpoint: str      # /api/report / /api/alert
    payload: dict
    status: str        # PENDING / SENDING / SENT / FAILED
    retry_count: int
    next_retry_at: float
    created_at: float


class OfflineQueue:
    """SQLite 离线队列，线程安全。"""

    def __init__(self, db_path: str = "offline_queue.db") -> None:
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        self._init_db()
        self._recover_stuck_items()

    def _init_db(self) -> None:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS offline_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    next_retry_at REAL NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )"""
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_queue_status_retry ON offline_queue(status, next_retry_at)"
            )

    def _recover_stuck_items(self) -> None:
        """启动时恢复：把上次崩溃时卡在 SENDING 的记录重置为 PENDING。"""
        now = time.time()
        with self._lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "UPDATE offline_queue SET status='PENDING', updated_at=? WHERE status='SENDING'",
                (now,),
            )
            if cur.rowcount > 0:
                logger.warning("恢复了 %d 条卡在 SENDING 的队列记录", cur.rowcount)

    # === 入队 ===

    def enqueue_report(self, payload: dict) -> int:
        return self._enqueue("report", "/api/report", payload)

    def enqueue_alert(self, payload: dict) -> int:
        return self._enqueue("alert", "/api/alert", payload)

    def _enqueue(self, type_: str, endpoint: str, payload: dict) -> int:
        now = time.time()
        with self._lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """INSERT INTO offline_queue
                   (type, endpoint, payload, status, retry_count, next_retry_at, created_at, updated_at)
                   VALUES (?, ?, ?, 'PENDING', 0, ?, ?, ?)""",
                (type_, endpoint, json.dumps(payload, ensure_ascii=False), now, now, now),
            )
            item_id = cur.lastrowid
            logger.info("入队 %s (id=%d)，队列长度=%d", endpoint, item_id, self._count_pending())
            return item_id

    # === 出队 / 状态更新 ===

    def get_retryable(self, limit: int = 10) -> list[QueueItem]:
        """取可重试的记录：PENDING 且 next_retry_at <= now。
        alert 优先，然后按 next_retry_at 升序。
        """
        now = time.time()
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT * FROM offline_queue
                   WHERE status='PENDING' AND next_retry_at <= ?
                   ORDER BY CASE type WHEN 'alert' THEN 0 ELSE 1 END, next_retry_at ASC
                   LIMIT ?""",
                (now, limit),
            ).fetchall()
            return [self._row_to_item(r) for r in rows]

    def mark_sending(self, item_id: int) -> None:
        now = time.time()
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE offline_queue SET status='SENDING', updated_at=? WHERE id=?",
                (now, item_id),
            )

    def mark_sent(self, item_id: int) -> None:
        now = time.time()
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE offline_queue SET status='SENT', updated_at=? WHERE id=?",
                (now, item_id),
            )

    def mark_failed_after_retry(self, item_id: int, max_retries: int = 10) -> None:
        """发送失败：retry_count+1，计算下次重试时间。超过最大重试置 FAILED。"""
        now = time.time()
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT retry_count FROM offline_queue WHERE id=?", (item_id,),
            ).fetchone()
            if row is None:
                return
            new_retry = row[0] + 1

            if new_retry >= max_retries:
                conn.execute(
                    "UPDATE offline_queue SET status='FAILED', retry_count=?, updated_at=? WHERE id=?",
                    (new_retry, now, item_id),
                )
                logger.error("队列 item %d 超过最大重试 %d 次，置 FAILED", item_id, max_retries)
            else:
                # 退避策略：2^retry * 5秒，最大300秒
                delay = min((2 ** new_retry) * 5, 300)
                next_at = now + delay
                conn.execute(
                    """UPDATE offline_queue
                       SET retry_count=?, next_retry_at=?, updated_at=?, status='PENDING'
                       WHERE id=?""",
                    (new_retry, next_at, now, item_id),
                )
                logger.info(
                    "队列 item %d 第 %d 次重试失败，%.0f 秒后再试",
                    item_id, new_retry, delay,
                )

    # === 清理 ===

    def cleanup_old(self, days: int = 7) -> int:
        """清理 7 天前已 SENT 的记录。返回删除条数。"""
        cutoff = time.time() - days * 86400
        with self._lock, sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "DELETE FROM offline_queue WHERE status='SENT' AND created_at < ?",
                (cutoff,),
            )
            return cur.rowcount

    def stats(self) -> dict:
        """返回队列统计信息。"""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status='PENDING' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status='SENT' THEN 1 ELSE 0 END) as sent,
                    SUM(CASE WHEN status='FAILED' THEN 1 ELSE 0 END) as failed
                   FROM offline_queue"""
            ).fetchone()
            return {
                "total": row[0] or 0,
                "pending": row[1] or 0,
                "sent": row[2] or 0,
                "failed": row[3] or 0,
            }

    # === 辅助 ===

    def _count_pending(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM offline_queue WHERE status='PENDING'"
            ).fetchone()
            return row[0]

    def _row_to_item(self, row: sqlite3.Row) -> QueueItem:
        return QueueItem(
            id=row["id"],
            type=row["type"],
            endpoint=row["endpoint"],
            payload=json.loads(row["payload"]),
            status=row["status"],
            retry_count=row["retry_count"],
            next_retry_at=row["next_retry_at"],
            created_at=row["created_at"],
        )
