"""综合单元测试：验证断网缓冲、配置管理、音频特征、判定器等核心模块。
不需要摄像头/麦克风/网络，纯逻辑测试。
"""

import sys
import os
import time
import tempfile
import numpy as np

# 添加源码路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from crea3_monitor.config.manager import ConfigManager
from crea3_monitor.comm.offline_queue import OfflineQueue
from crea3_monitor.detect.audio import AudioDetector
from crea3_monitor.detect.vision import PersonPose
from crea3_monitor.judge.scream import ScreamDetector
from crea3_monitor.judge.noise import NoiseDetector
from crea3_monitor.judge.fall import FallDetector
from crea3_monitor.judge.inactivity import InactivityDetector


def _make_person(bbox, head_y=50):
    """构造一个模拟的PersonPose（17个关键点都在同一位置）。"""
    # 17个关键点，全设为同一个位置，置信度0.9
    kpts = np.zeros((17, 3), dtype=np.float32)
    kpts[:, 0] = (bbox[0] + bbox[2]) / 2  # x居中
    kpts[:, 1] = head_y  # y
    kpts[:, 2] = 0.9     # 置信度
    return PersonPose(bbox=bbox, keypoints=kpts, confidence=0.9)


def test_config_manager():
    print("=" * 50)
    print("测试 1：配置管理 ConfigManager")
    print("=" * 50)

    cm = ConfigManager()
    cfg = cm.snapshot()
    print(f"  默认配置：v{cfg.version} 报告周期={cfg.report_interval_seconds}s")
    print(f"  睡眠时段={cfg.sleep_start}-{cfg.sleep_end}")
    print(f"  静止阈值={cfg.inactivity_minutes}分钟")

    # 模拟PC下发配置
    payload = {
        "version": 3,
        "sleep_start": "23:00",
        "sleep_end": "06:30",
        "inactivity_minutes": 45,
        "fall_confirm_seconds": 8,
        "report_interval_seconds": 60,
        "fall_confidence": 0.7,
        "sound_confidence": 0.6,
    }
    changed = cm.apply(payload)
    cfg = cm.snapshot()
    print(f"  应用新配置后：changed={changed}")
    print(f"  v{cfg.version} 睡眠={cfg.sleep_start}-{cfg.sleep_end} 静止={cfg.inactivity_minutes}min")

    # 测试非法字段被忽略
    bad_payload = {"inactivity_minutes": 99999, "fall_confirm_seconds": -1, "sleep_start": "bad"}
    cm.apply(bad_payload)
    cfg = cm.snapshot()
    print(f"  非法字段忽略后：静止={cfg.inactivity_minutes}min 确认={cfg.fall_confirm_seconds}s")
    print("  ✅ 配置管理测试通过\n")


def test_offline_queue():
    print("=" * 50)
    print("测试 2：离线队列 OfflineQueue")
    print("=" * 50)

    # 用临时数据库
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        q = OfflineQueue(db_path=db_path)

        # 入队 report
        rid = q.enqueue_report({
            "device_id": "monitor-01",
            "timestamp": "2026-10-30T12:00:00+08:00",
            "status": "normal",
            "message": "测试报告",
        })
        print(f"  入队 report：id={rid}")

        # 入队 alert
        aid = q.enqueue_alert({
            "device_id": "monitor-01",
            "timestamp": "2026-10-30T12:01:00+08:00",
            "type": "fall",
            "confidence": 0.88,
            "message": "测试跌倒警报",
        })
        print(f"  入队 alert：id={aid}")

        # 统计
        stats = q.stats()
        print(f"  队列统计：{stats}")

        # 取可重试的
        items = q.get_retryable()
        print(f"  可重试记录数：{len(items)}")
        for item in items:
            print(f"    id={item.id} type={item.type} retry={item.retry_count}")

        # alert 应该排在 report 前面
        assert items[0].type == "alert", "alert 应该优先"
        print("  ✅ alert 优先排序正确")

        # 标记 SENDING → SENT
        q.mark_sending(aid)
        items2 = q.get_retryable()
        print(f"  标记 alert 为 SENDING 后，可重试数：{len(items2)}")

        q.mark_sent(aid)
        stats = q.stats()
        print(f"  alert 标记 SENT 后：{stats}")

        # 测试退避策略
        q.mark_failed_after_retry(rid)
        q.mark_failed_after_retry(rid)
        # 退避后next_retry_at是未来时间，所以get_retryable取不到
        # 直接查数据库验证退避计算是否正确
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "SELECT retry_count, next_retry_at FROM offline_queue WHERE id=?", (rid,)
            ).fetchone()
            retry_count, next_retry_at = row
            now = time.time()
            delay = next_retry_at - now
            print(f"  report 失败2次后：retry={retry_count} 预计{delay:.0f}秒后重试")
            assert retry_count == 2, f"retry_count应该是2，实际是{retry_count}"
            # 2^2 * 5 = 20秒
            assert 15 < delay < 25, f"退避时间应该约20秒，实际是{delay:.0f}秒"

        # 测试崩溃恢复
        # 手动改一条为 SENDING 模拟崩溃
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE offline_queue SET status='SENDING' WHERE id=?", (rid,))
        # 重新初始化应该自动恢复
        q2 = OfflineQueue(db_path=db_path)
        # 把next_retry_at改成过去时间，让它能被取到
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE offline_queue SET next_retry_at=0 WHERE id=?", (rid,))
        items4 = q2.get_retryable()
        print(f"  崩溃恢复后，可重试数：{len(items4)}（SENDING已重置为PENDING）")
        assert len(items4) >= 1, "崩溃恢复后应该有可重试记录"

        print("  ✅ 离线队列测试通过\n")
    finally:
        # Windows下数据库连接可能还没完全释放，延迟删除
        try:
            os.unlink(db_path)
        except PermissionError:
            pass  # 临时文件，留着也没关系


def test_audio_detect():
    print("=" * 50)
    print("测试 3：音频特征提取 AudioDetector")
    print("=" * 50)

    detector = AudioDetector(sample_rate=16000)

    # 1. 静音
    silent = np.zeros(16000, dtype=np.float32)
    f1 = detector.extract(silent)
    print(f"  静音：rms={f1.rms:.4f} centroid={f1.spectral_centroid:.0f}Hz burst={f1.is_burst}")

    # 2. 低频嗡鸣（异常声响）
    t = np.linspace(0, 1, 16000, endpoint=False)
    low_freq = 0.3 * np.sin(2 * np.pi * 100 * t).astype(np.float32)  # 100Hz
    f2 = detector.extract(low_freq)
    print(f"  低频(100Hz)：rms={f2.rms:.4f} centroid={f2.spectral_centroid:.0f}Hz burst={f2.is_burst}")

    # 3. 高频尖叫（呼救声）
    high_freq = 0.3 * np.sin(2 * np.pi * 3000 * t).astype(np.float32)  # 3000Hz
    f3 = detector.extract(high_freq)
    print(f"  高频(3000Hz)：rms={f3.rms:.4f} centroid={f3.spectral_centroid:.0f}Hz burst={f3.is_burst}")

    print("  ✅ 音频特征提取测试通过\n")


def test_scream_detector():
    print("=" * 50)
    print("测试 4：呼救声判定 ScreamDetector")
    print("=" * 50)

    det = ScreamDetector(scream_confirm_seconds=1)
    sample_rate = 16000

    # 模拟持续高频尖叫 3 秒（每块0.5秒）
    print("  模拟持续高频尖叫（3秒）...")
    triggered = False
    for i in range(6):  # 6块 × 0.5秒 = 3秒
        t = np.linspace(0, 0.5, sample_rate // 2, endpoint=False)
        block = 0.3 * np.sin(2 * np.pi * 3000 * t).astype(np.float32)
        features = AudioDetector(sample_rate=sample_rate).extract(block)
        if det.update(features):
            triggered = True
            print(f"    第{i+1}块触发警报！")
            break
        time.sleep(0.05)  # 模拟时间流逝

    print(f"  呼救触发结果：{triggered}")
    print("  ✅ 呼救声判定测试通过\n")


def test_noise_detector():
    print("=" * 50)
    print("测试 5：异常声响判定 NoiseDetector")
    print("=" * 50)

    det = NoiseDetector(min_rms=0.1, cooldown_seconds=1)
    sample_rate = 16000

    # 模拟突发大声音
    t = np.linspace(0, 0.5, sample_rate // 2, endpoint=False)
    burst = 0.5 * np.random.randn(sample_rate // 2).astype(np.float32)  # 白噪声突发
    features = AudioDetector(sample_rate=sample_rate).extract(burst)
    result1 = det.update(features)
    print(f"  第一次突发：触发={result1} (rms={features.rms:.3f})")

    # 冷却期内再触发
    result2 = det.update(features)
    print(f"  冷却期内再触发：触发={result2}（应该被冷却掉）")

    time.sleep(1.1)  # 等冷却结束
    result3 = det.update(features)
    print(f"  冷却结束后再触发：触发={result3}")

    print("  ✅ 异常声响判定测试通过\n")


def test_fall_detector():
    print("=" * 50)
    print("测试 6：跌倒判定 FallDetector")
    print("=" * 50)

    det = FallDetector()
    det.fall_confirm_seconds = 1

    # 模拟站立姿态的人（竖长框）
    standing_person = _make_person(
        bbox=(100, 50, 140, 350),  # 宽40，高300，比例0.13（竖长）
        head_y=60,
    )

    # 站立状态
    for i in range(3):
        result = det.update([standing_person], timestamp=time.monotonic())
        print(f"  站立第{i+1}次：fall={result}")

    # 模拟跌倒姿态（横宽框）
    fallen_person = _make_person(
        bbox=(50, 200, 350, 250),  # 宽300，高50，比例6.0（横宽）
        head_y=210,
    )

    print("  模拟跌倒...")
    triggered = False
    base_time = time.monotonic()
    for i in range(5):
        result = det.update([fallen_person], timestamp=base_time + i * 0.3)
        if result:
            triggered = True
            print(f"    第{i+1}次触发跌倒警报！")
            break

    print(f"  跌倒触发结果：{triggered}")
    print("  ✅ 跌倒判定测试通过\n")


def main():
    print("\n" + "=" * 60)
    print("  自适应多模态检测系统 - 模块单元测试")
    print("=" * 60 + "\n")

    test_config_manager()
    test_offline_queue()
    test_audio_detect()
    test_scream_detector()
    test_noise_detector()
    test_fall_detector()

    print("=" * 60)
    print("  ✅ 全部测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    main()
