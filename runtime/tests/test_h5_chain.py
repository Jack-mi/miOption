from __future__ import annotations

import json
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from mioption_runtime.futu.quote import MockQuoteBackend
from mioption_runtime.futu.quote_store import QuoteStore
from mioption_runtime.ingress.h5 import H5Server
from mioption_runtime.seller.desk import SellerDesk
from mioption_runtime.seller.store import SellerStore


def _json(url: str, method: str = "GET", payload: dict | None = None, timeout: float = 5) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _err(url: str, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
    try:
        _json(url, method, payload)
        raise AssertionError("expected HTTP error")
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def _pack(underlying: str = "US.BIDU", last: float = 99.47) -> dict:
    return {
        "ok": True,
        "underlying": underlying,
        "pulled_at": "2026-09-07T08:00:00+00:00",
        "source": "futu",
        "days": 60,
        "windows": [{"start": "2026-09-07", "end": "2026-10-06"}],
        "coverage": {"chain_contracts": 2, "with_greeks": 2, "with_quote": 2},
        "equity": {
            "code": underlying,
            "name": "Baidu",
            "last_price": last,
            "bid_price": 99.4,
            "ask_price": 99.5,
            "change_val": -0.53,
            "change_rate": -0.53,
        },
        "options": [
            {
                "code": f"{underlying}260911C100000",
                "option_type": "CALL",
                "strike_time": "2026-09-11",
                "option_strike_price": 100.0,
                "bid_price": 2.1,
                "ask_price": 2.3,
                "last_price": 2.2,
                "option_delta": 0.48,
                "option_implied_volatility": 38.2,
                "noise": "keep-in-extra",
            },
            {
                "code": f"{underlying}260911P100000",
                "option_type": "PUT",
                "strike_time": "2026-09-11",
                "option_strike_price": 100.0,
                "bid_price": 2.4,
                "ask_price": 2.6,
                "last_price": 2.5,
                "option_delta": -0.52,
                "option_implied_volatility": 39.1,
            },
        ],
    }


def _server(tmp_path: Path, pull_fn=None) -> H5Server:
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text('<a href="chain.html">行情</a>', encoding="utf-8")
    (static / "chain.html").write_text("<section id='chain'></section>", encoding="utf-8")
    store = QuoteStore(tmp_path / "quotes.sqlite")
    desk = SellerDesk(store=SellerStore(tmp_path / "seller"), quote=MockQuoteBackend())
    return H5Server(
        "127.0.0.1",
        0,
        static_root=static,
        desk=desk,
        quote_store=store,
        pull_fn=pull_fn or (lambda underlying, days=60: _pack(underlying)),
    )


def test_h5_chain_get_empty_and_after_pull(tmp_path: Path):
    server = _server(tmp_path)
    server.start_background()
    base = f"http://127.0.0.1:{server.port}"
    try:
        page = urlopen(f"{base}/chain.html", timeout=5).read().decode()
        assert "id='chain'" in page or 'id="chain"' in page
        empty = _json(f"{base}/api/chain?q=bidu")
        assert empty["ok"] is True
        assert empty["empty"] is True
        assert empty["underlying"] == "US.BIDU"
        assert empty["place_order"] is False
        pulled = _json(f"{base}/api/chain/pull", "POST", {"underlyings": "百度", "days": 60})
        assert pulled["ok"] is True
        assert pulled["place_order"] is False
        assert pulled["underlying"] == "US.BIDU"
        assert pulled["equity"]["last_price"] == 99.47
        assert pulled["count"] == 2
        assert pulled["expiries"] == ["2026-09-11"]
        got = _json(f"{base}/api/chain?q=BIDU")
        assert got.get("empty") is not True
        assert got["equity"]["last_price"] == 99.47
        assert got["chain"][0]["strikes"][0]["call"]["iv"] == 38.2
        detail = _json(f"{base}/api/chain/contract?q=bidu&code=US.BIDU260911C100000")
        assert detail["extra"]["noise"] == "keep-in-extra"
        assert detail["place_order"] is False
    finally:
        server.stop()


def test_h5_chain_get_requires_q(tmp_path: Path):
    server = _server(tmp_path)
    server.start_background()
    try:
        code, body = _err(f"http://127.0.0.1:{server.port}/api/chain")
        assert code == 400
        assert body["error"] == "q_required"
        assert body["place_order"] is False
    finally:
        server.stop()


def test_h5_chain_pull_one_at_a_time(tmp_path: Path):
    started = threading.Event()
    release = threading.Event()

    def slow_pull(underlying: str, days: int = 60) -> dict:
        started.set()
        release.wait(timeout=2)
        return _pack(underlying)

    server = _server(tmp_path, pull_fn=slow_pull)
    server.start_background()
    base = f"http://127.0.0.1:{server.port}"
    first: dict = {}

    def run_first() -> None:
        first.update(_json(f"{base}/api/chain/pull", "POST", {"underlyings": "US.BIDU"}, timeout=5))

    try:
        t = threading.Thread(target=run_first)
        t.start()
        assert started.wait(timeout=2)
        code, body = _err(f"{base}/api/chain/pull", "POST", {"underlyings": "US.BIDU"})
        assert code == 409
        assert body["error"] == "pull_in_progress"
        release.set()
        t.join(timeout=5)
        assert first.get("ok") is True
    finally:
        release.set()
        server.stop()


def test_h5_chain_pull_failure_does_not_hit_opend(tmp_path: Path):
    def boom(underlying: str, days: int = 60) -> dict:
        raise RuntimeError("OpenD not reachable at 127.0.0.1:11111; start and login OpenD first")

    server = _server(tmp_path, pull_fn=boom)
    server.start_background()
    try:
        code, body = _err(
            f"http://127.0.0.1:{server.port}/api/chain/pull",
            "POST",
            {"underlyings": "US.BIDU"},
        )
        assert code == 500
        assert "OpenD" in body["error"]
        assert body["place_order"] is False
        empty = _json(f"http://127.0.0.1:{server.port}/api/chain?q=US.BIDU")
        assert empty["empty"] is True
    finally:
        server.stop()


def test_vault_map_exposes_chain_ui():
    vault = Path(__file__).resolve().parents[2] / "docs" / "vault-map"
    home = (vault / "index.html").read_text(encoding="utf-8")
    desk = (vault / "desk.html").read_text(encoding="utf-8")
    chain = (vault / "chain.html").read_text(encoding="utf-8")
    chat = (vault / "chat.html").read_text(encoding="utf-8")
    js = (vault / "chain.js").read_text(encoding="utf-8")
    assert 'href="chain.html"' in home
    assert 'href="chain.html"' in desk
    assert 'href="chat.html"' in home
    assert 'href="chat.html"' in desk
    assert 'href="chat.html"' in chain
    assert 'id="chain"' in chain
    assert 'class="gpt"' in chat
    assert "gpt-sessions" in chat
    assert "chat-launch" not in chain
    assert "/api/chain" in js
    assert "/api/chain/pull" in js
    assert "next_beyond" in js
    assert "place_order" in js or "不下单" in chain
    assert "采纳" not in chain
    assert "拒绝" not in chain
