"""Local H5 server: vault-map static files + seller-desk + chain JSON API. No orders."""

from __future__ import annotations

import json
import mimetypes
import os
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from ..futu.quote_store import QuoteStore
from ..seller.desk import SellerDesk
from ..seller.scan import DEFAULT_WATCHLIST, resolve_underlyings

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STATIC = REPO_ROOT / "docs" / "vault-map"

PullFn = Callable[..., dict[str, Any]]


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or 0)
    if length < 0 or length > 65536:
        raise ValueError("request body exceeds 64 KiB")
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("JSON object required")
    return payload


def _underlyings_from(raw: Any) -> list[str]:
    if raw in (None, ""):
        return []
    if isinstance(raw, str):
        return resolve_underlyings(raw)
    if isinstance(raw, list):
        return resolve_underlyings(raw)
    return []


def _empty_chain(underlying: str) -> dict[str, Any]:
    return {
        "ok": True,
        "empty": True,
        "place_order": False,
        "underlying": underlying,
        "equity": None,
        "contracts": [],
        "chain": [],
        "expiries": [],
        "count": 0,
    }


def _default_pull(underlying: str, *, days: int = 60) -> dict[str, Any]:
    from ..futu.quote import mock_underlying_pack, pull_underlying_pack

    if os.environ.get("MIOPTION_FUTU_MOCK", "1") == "1":
        return mock_underlying_pack(underlying, days=days)
    return pull_underlying_pack(underlying, days=days)


def create_h5_handler(
    static_root: Path,
    desk: SellerDesk,
    *,
    quote_store: QuoteStore | None = None,
    pull_fn: PullFn | None = None,
) -> type[BaseHTTPRequestHandler]:
    root = static_root.resolve()
    store_holder: dict[str, QuoteStore | None] = {"store": quote_store}
    puller = pull_fn or _default_pull
    pull_lock = threading.Lock()
    mutation_lock = threading.RLock()

    def store() -> QuoteStore:
        if store_holder["store"] is None:
            store_holder["store"] = QuoteStore()
        return store_holder["store"]

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def _cors(self) -> None:
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def _local_host(self) -> bool:
            host = urlparse("//" + self.headers.get("Host", "")).hostname
            if host not in ("127.0.0.1", "localhost", "::1"):
                self._json(403, {"ok": False, "error": "loopback_host_required"})
                return False
            return True

        def _bytes(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self._cors()
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, payload: dict[str, Any]) -> None:
            self._bytes(code, json.dumps(payload, default=str).encode("utf-8"), "application/json; charset=utf-8")

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            if not self._local_host():
                return
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)
            if path == "/api/config":
                model = os.environ.get("MIOPTION_CHAT_MODEL", "opencode-go/deepseek-v4-flash")
                provider, model_id = model.split("/", 1)
                self._json(200, {
                    "workspace": str(REPO_ROOT),
                    "opencode_url": os.environ.get("MIOPTION_CHAT_URL", "http://127.0.0.1:4096"),
                    "model": {"providerID": provider, "modelID": model_id},
                    "place_order": False,
                })
                return
            if path == "/api/wiki":
                from ..agent.wiki import wiki_query

                self._json(200, wiki_query((query.get("q") or [""])[0]))
                return
            if path == "/api/wiki/page":
                from ..agent.wiki import wiki_page

                try:
                    self._json(200, wiki_page((query.get("path") or [""])[0]))
                except (ValueError, OSError):
                    self._json(404, {"ok": False, "error": "page_not_found"})
                return
            if path in ("/api/health", "/api/seller/health"):
                snap = desk.snapshot()
                self._json(
                    200,
                    {
                        "ok": True,
                        "service": "mioption-h5",
                        "mock": snap["mock"],
                        "count": snap["count"],
                        "place_order": False,
                    },
                )
                return
            if path in ("/api/seller", "/api/seller/cards"):
                status = (query.get("status") or [None])[0] or None
                q = (query.get("q") or query.get("underlyings") or [None])[0] or None
                self._json(200, desk.snapshot(status=status, query=q))
                return
            if path == "/api/seller/events":
                self._json(200, {"ok": True, "events": desk.store.list_events(), "place_order": False})
                return
            if path == "/api/chain":
                names = _underlyings_from((query.get("q") or query.get("underlyings") or [None])[0])
                if not names:
                    self._json(400, {"ok": False, "error": "q_required", "place_order": False})
                    return
                pack = store().current(names[0])
                self._json(200, pack if pack else _empty_chain(names[0]))
                return
            if path == "/api/chain/contract":
                names = _underlyings_from((query.get("q") or query.get("underlyings") or [None])[0])
                code = (query.get("code") or [""])[0]
                if not names or not code:
                    self._json(400, {"ok": False, "error": "q_and_code_required", "place_order": False})
                    return
                detail = store().get_contract(names[0], code)
                if detail is None:
                    self._json(404, {"ok": False, "error": "not_found", "place_order": False})
                    return
                self._json(200, detail)
                return
            self._static(path)

        def do_POST(self) -> None:  # noqa: N802
            if not self._local_host():
                return
            origin = self.headers.get("Origin")
            if origin and urlparse(origin).netloc != self.headers.get("Host"):
                self._json(403, {"ok": False, "error": "cross_origin_write_denied"})
                return
            if urlparse(self.path).path.startswith("/api/seller/"):
                with mutation_lock:
                    self._post()
            else:
                self._post()

        def _post(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            try:
                body = _read_json(self)
                if path == "/api/seller/scan":
                    raw = body.get("underlyings")
                    if raw in (None, ""):
                        names = list(DEFAULT_WATCHLIST)
                    elif isinstance(raw, str):
                        names = resolve_underlyings(raw)
                    elif isinstance(raw, list):
                        names = resolve_underlyings(raw)
                    else:
                        names = list(DEFAULT_WATCHLIST)
                    if not names:
                        self._json(400, {"ok": False, "error": "no_symbols", "cards": [], "count": 0})
                        return
                    self._json(200, desk.scan(names))
                    return
                if path == "/api/seller/verdict":
                    card_id = str(body.get("card_id") or "")
                    verdict = str(body.get("verdict") or "")
                    note = str(body.get("note") or "")
                    if not card_id or not verdict:
                        self._json(400, {"ok": False, "error": "card_id and verdict required"})
                        return
                    result = desk.verdict(card_id, verdict, note=note)
                    self._json(200 if result.get("ok") else 400, result)
                    return
                if path == "/api/seller/monitor":
                    self._json(200, desk.monitor_tick())
                    return
                if path == "/api/chain/pull":
                    if not pull_lock.acquire(blocking=False):
                        self._json(409, {"ok": False, "error": "pull_in_progress", "place_order": False})
                        return
                    try:
                        names = _underlyings_from(body.get("underlyings", body.get("q")))
                        if not names:
                            self._json(400, {"ok": False, "error": "no_symbols", "place_order": False})
                            return
                        days = int(body.get("days") or 60)
                        if not 1 <= days <= 90 or len(names) > 8:
                            raise ValueError("pull allows 1-90 days and at most 8 symbols")
                        results: list[dict[str, Any]] = []
                        for name in names:
                            pack = puller(name, days=days)
                            store().replace_current(pack)
                            current = store().current(name)
                            if current:
                                results.append(current)
                        out: dict[str, Any] = {
                            "ok": True,
                            "place_order": False,
                            "results": results,
                        }
                        if len(results) == 1:
                            packed = dict(results[0])
                            packed.update(out)
                            out = packed
                        else:
                            out["count"] = len(results)
                        self._json(200, out)
                    finally:
                        pull_lock.release()
                    return
            except ValueError as exc:
                self._json(400, {"ok": False, "error": str(exc), "place_order": False})
                return
            except Exception as exc:  # noqa: BLE001
                self._json(500, {"ok": False, "error": str(exc), "place_order": False})
                return
            self._json(404, {"ok": False, "message": "not found"})

        def _static(self, path: str) -> None:
            rel = unquote(path).lstrip("/") or "index.html"
            target = (root / rel).resolve()
            if not target.is_relative_to(root):
                self._json(403, {"ok": False, "error": "forbidden"})
                return
            if not target.is_file():
                if path == "/" or not path.rsplit("/", 1)[-1].count("."):
                    index = root / "index.html"
                    if index.is_file():
                        self._file(index)
                        return
                self._json(404, {"ok": False, "message": "not found"})
                return
            self._file(target)

        def _file(self, target: Path) -> None:
            mime, _ = mimetypes.guess_type(str(target))
            if target.suffix == ".js":
                mime = "text/javascript; charset=utf-8"
            elif target.suffix == ".css":
                mime = "text/css; charset=utf-8"
            elif target.suffix == ".html":
                mime = "text/html; charset=utf-8"
            self._bytes(200, target.read_bytes(), mime or "application/octet-stream")

    return Handler


class H5Server:
    def __init__(
        self,
        host: str,
        port: int,
        *,
        static_root: Path | None = None,
        desk: SellerDesk | None = None,
        quote_store: QuoteStore | None = None,
        pull_fn: PullFn | None = None,
    ):
        qs = quote_store
        if desk is None:
            qs = qs if qs is not None else QuoteStore()
            desk = SellerDesk(quote_store=qs)
        elif qs is not None and getattr(desk, "quote_store", None) is None:
            desk.quote_store = qs
        handler = create_h5_handler(
            Path(static_root or DEFAULT_STATIC),
            desk,
            quote_store=qs,
            pull_fn=pull_fn,
        )
        self.httpd = ThreadingHTTPServer((host, port), handler)
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        return int(self.httpd.server_address[1])

    def start_background(self) -> None:
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()

    def serve_forever(self) -> None:
        self.httpd.serve_forever()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        if self._thread:
            self._thread.join(timeout=2)
