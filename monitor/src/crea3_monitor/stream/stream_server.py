"""统一推流服务：MJPEG 视频 + WebSocket 音频 + 健康检查。

- 视频：GET /stream/video（multipart/x-mixed-replace，支持 X-Auth-Token 或 ?token=）
- 音频：WS /stream/audio（float32 PCM 二进制帧，支持 token 子协议或 ?token=）
- 健康：GET /health（无需鉴权）

设计：
- 视频用 Flask（werkzeug 同步服务器），和现有代码一致
- 音频用 websockets 库在独立线程跑异步服务器，不阻塞 Flask
- FrameHub / AudioHub 解耦采集端和推流端
"""

from __future__ import annotations

import asyncio
import hmac
import logging
import threading
from typing import Iterator

import numpy as np
from flask import Flask, Response, jsonify, request
from werkzeug.serving import make_server

logger = logging.getLogger(__name__)

BOUNDARY = "frame"


# === 帧中枢 ===

class FrameHub:
    """最新帧中枢：采集线程写入，所有预览客户端各自读取，互不阻塞。"""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._jpeg: bytes | None = None
        self._sequence = 0
        self._closed = False

    def publish(self, jpeg: bytes) -> None:
        with self._condition:
            self._jpeg = jpeg
            self._sequence += 1
            self._condition.notify_all()

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()

    def wait_frame(self, last_sequence: int, timeout: float = 2.0) -> tuple[int, bytes] | None:
        with self._condition:
            if self._sequence == last_sequence and not self._closed:
                self._condition.wait(timeout)
            if self._closed or self._jpeg is None or self._sequence == last_sequence:
                return None
            return self._sequence, self._jpeg

    def stream(self) -> Iterator[bytes]:
        """按产出顺序逐帧生成 JPEG，供 multipart/x-mixed-replace 响应使用。"""
        sequence = 0
        while True:
            frame = self.wait_frame(sequence)
            if frame is None:
                if self._closed:
                    return
                continue
            sequence, jpeg = frame
            yield jpeg


class AudioHub:
    """音频块中枢：采集线程写入，所有WS客户端广播。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: list[threading.Queue] = []
        self._closed = False

    def publish(self, block: np.ndarray) -> None:
        """发布一个音频块（float32 numpy数组）给所有订阅者。"""
        data = block.tobytes()
        with self._lock:
            dead = []
            for q in self._subscribers:
                try:
                    q.put_nowait(data)
                except threading.Queue.Full:
                    # 客户端跟不上，丢最旧的一块
                    try:
                        q.get_nowait()
                    except threading.Queue.Empty:
                        pass
                    try:
                        q.put_nowait(data)
                    except threading.Queue.Full:
                        dead.append(q)
            for q in dead:
                self._subscribers.remove(q)

    def subscribe(self) -> threading.Queue:
        with self._lock:
            q: threading.Queue = threading.Queue(maxsize=32)
            self._subscribers.append(q)
            return q

    def unsubscribe(self, q: threading.Queue) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._subscribers.clear()


# === Flask 视频服务 ===

def create_video_app(frame_hub: FrameHub, token: str) -> Flask:
    """创建 Flask 应用：视频流 + 健康检查。"""
    app = Flask(__name__)

    def authorized() -> bool:
        supplied = request.headers.get("X-Auth-Token") or request.args.get("token") or ""
        return hmac.compare_digest(supplied.encode(), token.encode())

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/stream/video")
    def video():
        if not authorized():
            return jsonify({"ok": False, "error": "unauthorized"}), 401

        def generate():
            try:
                for jpeg in frame_hub.stream():
                    yield (
                        b"--" + BOUNDARY.encode() + b"\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n"
                        + jpeg + b"\r\n"
                    )
            except GeneratorExit:
                return

        return Response(
            generate(),
            mimetype=f"multipart/x-mixed-replace; boundary={BOUNDARY}",
            headers={"Cache-Control": "no-store"},
        )

    return app


# === WebSocket 音频服务 ===

def start_audio_ws_server(
    audio_hub: AudioHub,
    token: str,
    host: str,
    port: int,
) -> tuple[threading.Thread, asyncio.AbstractEventLoop]:
    """在独立线程启动 WebSocket 音频服务器。

    返回 (线程, event_loop)，方便外部优雅关闭。
    需要 websockets 库（pip install websockets）。
    """
    import websockets  # 延迟导入，没装也不影响视频功能

    async def handler(websocket):
        # 鉴权：query 参数 或 子协议
        supplied = ""
        if websocket.request.path:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(websocket.request.path)
            qs = parse_qs(parsed.query)
            supplied = qs.get("token", [""])[0]
        if not supplied and websocket.subprotocols:
            # 备用：子协议里带token
            supplied = websocket.subprotocols[0] if len(websocket.subprotocols) > 0 else ""

        if not hmac.compare_digest(supplied.encode(), token.encode()):
            await websocket.close(code=1008, reason="unauthorized")
            return

        # 订阅音频流
        q = audio_hub.subscribe()
        logger.info("音频WS客户端已连接：%s", websocket.remote_address)
        try:
            while True:
                try:
                    data = q.get(timeout=5.0)
                    await websocket.send(data)
                except threading.Queue.Empty:
                    # 5秒没数据，发个ping保活
                    await websocket.ping()
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            audio_hub.unsubscribe(q)
            logger.info("音频WS客户端已断开")

    async def run_server():
        async with websockets.serve(handler, host, port):
            await asyncio.Future()  # 永久运行

    loop = asyncio.new_event_loop()
    thread = threading.Thread(
        target=lambda: asyncio.run(run_server()),
        name="audio-ws-server",
        daemon=True,
    )
    thread.start()
    logger.info("音频WebSocket服务已启动：ws://%s:%s/stream/audio", host, port)
    return thread, loop


# === 一键启动 ===

class StreamService:
    """统一推流服务管理器。"""

    def __init__(self, token: str, host: str, video_port: int, audio_ws_port: int) -> None:
        self.token = token
        self.host = host
        self.video_port = video_port
        self.audio_ws_port = audio_ws_port

        self.frame_hub = FrameHub()
        self.audio_hub = AudioHub()

        self._video_server = None
        self._audio_thread: threading.Thread | None = None
        self._audio_loop: asyncio.AbstractEventLoop | None = None

    def start(self) -> None:
        # 1. Flask 视频服务
        app = create_video_app(self.frame_hub, self.token)
        self._video_server = make_server(self.host, self.video_port, app, threaded=True)
        logger.info("MJPEG视频服务已启动：http://%s:%s/stream/video", self.host, self.video_port)

        video_thread = threading.Thread(
            target=self._video_server.serve_forever,
            name="mjpeg-server",
            daemon=True,
        )
        video_thread.start()

        # 2. WebSocket 音频服务
        try:
            self._audio_thread, self._audio_loop = start_audio_ws_server(
                self.audio_hub, self.token, self.host, self.audio_ws_port,
            )
        except ImportError:
            logger.warning("websockets 库未安装，音频WS推流已禁用（pip install websockets）")

    def shutdown(self) -> None:
        self.frame_hub.close()
        self.audio_hub.close()
        if self._video_server is not None:
            self._video_server.shutdown()
        if self._audio_loop is not None:
            self._audio_loop.call_soon_threadsafe(self._audio_loop.stop)
        logger.info("推流服务已关闭")
