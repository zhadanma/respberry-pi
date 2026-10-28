"""配置管理模块：保存并对外提供当前配置。

配置由 PC 端设置、监控端拉取。断连时沿用最近一次有效配置。
"""

from .manager import ConfigManager, RuntimeConfig
from .settings import Settings, load_settings

__all__ = ["ConfigManager", "RuntimeConfig", "Settings", "load_settings"]
