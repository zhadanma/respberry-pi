"""判定与状态机：核心业务逻辑。

依据检测结果 + 配置 + 时间，判定 A-1 跌倒、A-2 非睡眠时段长时间静止、
A-3 呼救声、A-4 异常声响。
"""

from .fall import FallDetector
from .inactivity import InactivityDetector
from .scream import ScreamDetector
from .noise import NoiseDetector

__all__ = ["FallDetector", "InactivityDetector", "ScreamDetector", "NoiseDetector"]
