"""
fat-chess HTTP 桥：在插件后端进程内启动 127.0.0.1 本地 HTTP 服务，
供宿主"下棋 MCP 工具"（requestUrl 类型）回调本进程执行棋局操作，
与 JSON-RPC 通道共享同一会话存储与动作分发（engine.service.handle_rpc）。

端点：
- POST /fatchess/<game>/<action>   请求体为工具参数（gameId/move/...）
- GET  /fatchess/ping             健康检查
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional

from .base import GameError
from .service import GAMES, handle_rpc


class FatChessBridge:
    def __init__(self) -> None:
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._port: Optional[int] = None

    @property
    def port(self) -> Optional[int]:
        return self._port

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._port}"

    def start(self) -> int:
        if self._server is not None:
            return self._port or 0

        class Handler(BaseHTTPRequestHandler):
            bridge = self

            # 静音默认日志
            def log_message(self, fmt, *args):  # noqa: D401
                return

            def _send(self, code: int, payload: Dict[str, Any]) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:  # noqa: N802
                if self.path.rstrip("/") == "/fatchess/ping":
                    self._send(200, {"ok": True, "status": "up"})
                else:
                    self._send(404, {"ok": False, "error": "not found"})

            def do_POST(self) -> None:  # noqa: N802
                path = self.path.rstrip("/")
                if not path.startswith("/fatchess/"):
                    self._send(404, {"ok": False, "error": "not found"})
                    return
                try:
                    _, _, game, action = path.split("/", 3)
                except ValueError:
                    self._send(400, {"ok": False, "error": "bad path"})
                    return
                if game not in GAMES:
                    self._send(400, {"ok": False, "error": f"unknown game: {game}"})
                    return
                try:
                    length = int(self.headers.get("Content-Length") or 0)
                    raw = self.rfile.read(length) if length else b"{}"
                    params = json.loads(raw.decode("utf-8") or "{}")
                    if not isinstance(params, dict):
                        params = {}
                except Exception as e:
                    self._send(400, {"ok": False, "error": f"bad request: {e}"})
                    return
                params = dict(params)
                params["game"] = game
                try:
                    result = handle_rpc(action, params)
                    self._send(200, {"ok": True, "data": result})
                except GameError as e:
                    self._send(200, {"ok": False, "error": str(e)})
                except Exception as e:  # noqa: BLE001
                    self._send(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})

        try:
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        except OSError as e:
            raise RuntimeError(f"无法启动 HTTP 桥: {e}") from e
        self._server = server
        self._port = int(server.server_address[1])
        self._thread = threading.Thread(target=server.serve_forever, daemon=True,
                                        name="fatchess-http-bridge")
        self._thread.start()
        return self._port

    def stop(self) -> None:
        if self._server is not None:
            try:
                self._server.shutdown()
            except Exception:
                pass
            try:
                self._server.server_close()
            except Exception:
                pass
            self._server = None
        self._port = None
        self._thread = None


_bridge = FatChessBridge()


def get_bridge() -> FatChessBridge:
    return _bridge
