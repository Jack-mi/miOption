"""OA-style webhook ingress on our own URLs (stdlib HTTP server)."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import urlparse


RunFn = Callable[[str, dict[str, Any]], dict[str, Any]]


def create_app_handler(run_webhook: RunFn) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:  # quieter tests
            return

        def _json(self, code: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path in ("/", "/health"):
                self._json(200, {"ok": True, "service": "mioption-webhooks"})
                return
            self._json(404, {"ok": False, "message": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            prefix = "/hooks/"
            if not path.startswith(prefix):
                self._json(404, {"ok": False, "message": "not found"})
                return
            hook_id = path[len(prefix) :].strip("/")
            if not hook_id:
                self._json(400, {"ok": False, "message": "missing webhook id"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json(400, {"ok": False, "message": "invalid json"})
                return
            if not isinstance(payload, dict):
                payload = {"value": payload}
            try:
                result = run_webhook(hook_id, payload)
            except Exception as exc:  # noqa: BLE001
                self._json(500, {"ok": False, "message": str(exc)})
                return
            self._json(200, result)

    return Handler


class WebhookServer:
    def __init__(self, host: str, port: int, run_webhook: RunFn):
        handler = create_app_handler(run_webhook)
        self.httpd = ThreadingHTTPServer((host, port), handler)
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        return int(self.httpd.server_address[1])

    def start_background(self) -> None:
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        if self._thread:
            self._thread.join(timeout=2)
