"""通信模块：与 PC 端交互。

由监控端主动发起：上报状态报告与异常警报、定期轮询拉取配置。
"""

from .client import PcClient

__all__ = ["PcClient"]
