"""监控端入口：python -m crea3_monitor [--send-alert]"""

from __future__ import annotations

import argparse
import logging
import sys

from .app import MonitorApp
from .config import load_settings


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crea3-monitor", description="自适应多模态检测系统 · 监控端")
    parser.add_argument(
        "--send-alert",
        action="store_true",
        help="发送一条演示警报后退出（用于验证 /api/alert 链路）",
    )
    args = parser.parse_args(argv)

    configure_logging()
    app = MonitorApp(load_settings())
    if args.send_alert:
        return 0 if app.send_demo_alert() else 1
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
