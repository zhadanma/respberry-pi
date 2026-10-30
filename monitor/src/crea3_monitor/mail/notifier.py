"""邮件通知：警报触发时给家属发邮件。

使用 SMTP_SSL，配置从 .env / config 读取。
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MailConfig:
    smtp_host: str       # 如 smtp.qq.com
    smtp_port: int       # 如 465 (SSL)
    sender_email: str
    sender_password: str  # 授权码，不是登录密码
    receiver_emails: list[str]


class MailNotifier:
    """邮件通知器。"""

    def __init__(self, config: MailConfig) -> None:
        self.config = config
        self._enabled = bool(config.smtp_host and config.sender_email and config.receiver_emails)
        if not self._enabled:
            logger.warning("邮件通知未配置，将跳过")

    def send_alert(self, alert_type: str, message: str, confidence: float) -> bool:
        """发送警报邮件。"""
        if not self._enabled:
            return False

        subject = f"【老人监护警报】{alert_type} - 置信度 {confidence:.0%}"
        body = f"""
        检测到异常事件：

        类型：{alert_type}
        描述：{message}
        置信度：{confidence:.0%}
        时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

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
            logger.info("警报邮件已发送至：%s", self.config.receiver_emails)
            return True
        except Exception as exc:
            logger.error("邮件发送失败：%s", exc)
            return False
