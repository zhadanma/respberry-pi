"""邮件通知：警报触发时给家属发邮件。

设计：
- 异步发送，主循环调用 send_alert 立刻返回，不阻塞视频/音频处理
- SMTP 在线程池里执行
"""

from __future__ import annotations

import logging
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MailConfig:
    smtp_host: str       # 如 smtp.qq.com
    smtp_port: int       # 如 465 (SSL)
    sender_email: str
    sender_password: str  # 授权码，不是登录密码
    receiver_emails: list[str]


class MailNotifier:
    """邮件通知器（异步）。"""

    def __init__(self, config: MailConfig) -> None:
        self.config = config
        self._enabled = bool(config.smtp_host and config.sender_email and config.receiver_emails)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mail")
        if not self._enabled:
            logger.warning("邮件通知未配置，将跳过")

    def send_alert(
        self,
        device_id: str,
        alert_type: str,
        confidence: float,
        message: str,
        has_clip: bool = False,
    ) -> None:
        """异步发送警报邮件，立刻返回，不阻塞主循环。

        参数：
            device_id: 设备ID
            alert_type: 警报类型（fall/inactivity/scream/noise）
            confidence: 置信度 0~1
            message: 详细描述
            has_clip: 是否附带视频片段
        """
        if not self._enabled:
            return

        # 提交到线程池，后台执行
        self._executor.submit(
            self._send_alert_sync,
            device_id, alert_type, confidence, message, has_clip,
        )

    def _send_alert_sync(
        self,
        device_id: str,
        alert_type: str,
        confidence: float,
        message: str,
        has_clip: bool,
    ) -> None:
        """实际发送逻辑，在后台线程执行。"""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        clip_text = "是（请登录PC端查看）" if has_clip else "否"

        subject = f"【老人监护警报】{alert_type} - {device_id}"
        body = f"""
        检测到异常事件：

        设备 ID：{device_id}
        异常类型：{alert_type}
        触发时间：{now_str}
        置信度：{confidence:.0%}
        详细描述：{message}
        是否含视频片段：{clip_text}

        请及时查看监控画面，确认老人安全。
        """

        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = self.config.sender_email
        msg["To"] = ", ".join(self.config.receiver_emails)
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            with smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port) as server:
                server.login(self.config.sender_email, self.config.sender_password)
                server.sendmail(
                    self.config.sender_email,
                    self.config.receiver_emails,
                    msg.as_string(),
                )
            logger.info("警报邮件已发送：%s", alert_type)
        except Exception as exc:
            logger.error("邮件发送失败：%s", exc)

    def shutdown(self) -> None:
        """程序退出时调用，等待线程池结束。"""
        self._executor.shutdown(wait=False)
