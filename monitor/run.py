"""监控端启动脚本：python run.py [--send-alert]"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from crea3_monitor.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
