"""最小 MJPEG 推流服务（阶段一用于调试与 PC 端预览）。

浏览器或 PC 端以 GET /stream/video 拉流，需携带 X-Auth-Token（或 ?token=）。
"""

from __future__ import annotations

import hmac
import logging

from flask import Flask, Response, jsonify, request
from werkzeug.serving import make_server

from .hub import FrameHub

logger = logging.getLogger(__name__)

BOUNDARY = "frame"


def create_app(hub: FrameHub, token: str) -> Flask:
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
                for jpeg in hub.stream():
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


def start_server(app: Flask, host: str, port: int):
    server = make_server(host, port, app, threaded=True)
    logger.info("MJPEG 推流服务已启动：http://%s:%s/stream/video", host, port)
    return server
