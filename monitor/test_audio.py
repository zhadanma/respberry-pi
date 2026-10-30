"""音频检测测试脚本。

用法：
python test_audio.py

设计：
- 音频回调里只做 queue.put()，绝对不做业务逻辑，避免底层缓冲溢出
- 主线程从 queue 取数据，做特征提取和判定
"""

from __future__ import annotations

import logging
import queue
import sys
import time
from pathlib import Path

import numpy as np
import sounddevice as sd

sys.path.insert(0, str(Path(__file__).parent / "src"))

from crea3_monitor.detect.audio import AudioDetector
from crea3_monitor.judge.scream import ScreamDetector
from crea3_monitor.judge.noise import NoiseDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("test_audio")

SAMPLE_RATE = 16000
BLOCK_SECONDS = 0.5
AUDIO_QUEUE_MAX = 20  # 最多缓存10秒音频，满了丢最旧的


def main() -> None:
    logger.info("音频检测测试（按 Ctrl+C 退出）...")

    detector = AudioDetector(sample_rate=SAMPLE_RATE)
    scream = ScreamDetector(scream_confirm_seconds=1)  # 测试用1秒
    noise = NoiseDetector(min_rms=0.1, cooldown_seconds=5)

    audio_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=AUDIO_QUEUE_MAX)
    block_size = int(SAMPLE_RATE * BLOCK_SECONDS)
    rms_history: list[float] = []

    # 音频回调：只入队，不做任何计算
    def callback(indata: np.ndarray, frames: int, time_info, status) -> None:
        if status:
            logger.warning("音频状态：%s", status)
        block = indata[:, 0].copy()
        try:
            audio_queue.put_nowait(block)
        except queue.Full:
            # 下游处理不过来，丢最旧的一块
            try:
                audio_queue.get_nowait()
            except queue.Empty:
                pass
            audio_queue.put_nowait(block)

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        blocksize=block_size,
        channels=1,
        dtype="float32",
        callback=callback,
    ):
        logger.info("麦克风已打开，开始采集...")
        try:
            while True:
                try:
                    block = audio_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                # 主线程：特征提取 + 判定
                features = detector.extract(block)
                rms_history.append(features.rms)
                if len(rms_history) > 20:
                    rms_history.pop(0)
                avg_rms = float(np.mean(rms_history))

                if scream.update(features):
                    logger.warning("🚨 触发呼救警报！")
                if noise.update(features):
                    logger.warning("🚨 触发异常声响警报！")

                bar = "#" * int(features.rms * 100)
                logger.info(
                    "RMS=%.3f avg=%.3f centroid=%.0fHz %s",
                    features.rms, avg_rms, features.spectral_centroid, bar,
                )

                time.sleep(0)  # 让出CPU
        except KeyboardInterrupt:
            logger.info("测试结束")


if __name__ == "__main__":
    main()
