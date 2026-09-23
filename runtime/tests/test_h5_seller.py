from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from mioption_runtime.futu.quote import MockQuoteBackend
from mioption_runtime.ingress.h5 import H5Server
from mioption_runtime.seller.desk import SellerDesk
from mioption_runtime.seller.scan import resolve_symbol, resolve_underlyings
from mioption_runtime.seller.store import SellerStore


def _json(url: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode())


def test_mock_scan_yields_credit_verticals(tmp_path: Path):
    desk = SellerDesk(store=SellerStore(tmp_path), quote=MockQuoteBackend())
    out = desk.scan(["US.SPY"])
    kinds = {c["structure_id"] for c in out["cards"]}
    assert out["count"] >= 2
    assert "bull_put_spread" in kinds
    assert "bear_call_spread" in kinds


def test_h5_seller_scan_verdict_monitor(tmp_path: Path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text('<a href="desk.html">研究台</a>', encoding="utf-8")
    (static / "desk.html").write_text(
        "<!doctype html><title>desk</title><section id='desk'></section>",
        encoding="utf-8",
    )
    store = SellerStore(tmp_path / "seller")
    desk = SellerDesk(store=store, quote=MockQuoteBackend())
    server = H5Server("127.0.0.1", 0, static_root=static, desk=desk)
    server.start_background()
    base = f"http://127.0.0.1:{server.port}"
    try:
        page = urlopen(f"{base}/desk.html", timeout=5).read().decode()
        assert 'id="desk"' in page or "id='desk'" in page
        health = _json(f"{base}/api/health")
        assert health["ok"] is True
        assert health["service"] == "mioption-h5"
        assert health["place_order"] is False
        scanned = _json(f"{base}/api/seller/scan", "POST", {"underlyings": "US.SPY"})
        assert scanned["count"] >= 2
        assert scanned.get("place_order") is not True
        card = scanned["cards"][0]
        judged = _json(
            f"{base}/api/seller/verdict",
            "POST",
            {"card_id": card["id"], "verdict": "adopt"},
        )
        assert judged["ok"] is True
        assert judged["card"]["verdict"] == "adopt"
        snap = _json(f"{base}/api/seller")
        assert any(c["id"] == card["id"] and c["verdict"] == "adopt" for c in snap["cards"])
        cleared = _json(
            f"{base}/api/seller/verdict",
            "POST",
            {"card_id": card["id"], "verdict": "clear"},
        )
        assert cleared["ok"] is True
        assert cleared["card"]["verdict"] in (None, "")
        assert cleared["card"]["status"] == "signal"
        snap = _json(f"{base}/api/seller")
        assert any(c["id"] == card["id"] and not c.get("verdict") for c in snap["cards"])
        monitored = _json(f"{base}/api/seller/monitor", "POST", {})
        assert monitored["ok"] is True
        assert monitored["place_order"] is False
    finally:
        server.stop()


def test_h5_does_not_expose_follow_submit(tmp_path: Path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<p>x</p>", encoding="utf-8")
    desk = SellerDesk(store=SellerStore(tmp_path / "seller"), quote=MockQuoteBackend())
    server = H5Server("127.0.0.1", 0, static_root=static, desk=desk)
    server.start_background()
    try:
        req = Request(
            f"http://127.0.0.1:{server.port}/api/seller/follow",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urlopen(req, timeout=5)
            raise AssertionError("follow endpoint should be absent")
        except HTTPError as exc:
            assert exc.code == 404
    finally:
        server.stop()


def test_resolve_nvidia_is_nvda_not_bidu():
    assert resolve_symbol("nvidia") == "US.NVDA"
    assert resolve_symbol("NVDA") == "US.NVDA"
    assert resolve_underlyings("nvidia") == ["US.NVDA"]
    assert "US.BIDU" not in resolve_underlyings("nvidia")


def test_scan_nvidia_does_not_return_bidu(tmp_path: Path):
    desk = SellerDesk(store=SellerStore(tmp_path), quote=MockQuoteBackend())
    desk.scan(["US.BIDU"])
    out = desk.scan(["nvidia"])
    assert out["watchlist"] == ["US.NVDA"]
    assert out["count"] >= 1
    assert all(c["underlying"] == "US.NVDA" for c in out["cards"])
    listed = desk.snapshot(query="nvidia")
    assert listed["count"] >= 1
    assert all(c["underlying"] == "US.NVDA" for c in listed["cards"])
    assert not any(c["underlying"] == "US.BIDU" for c in listed["cards"])


def test_h5_query_nvidia_hides_bidu(tmp_path: Path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "desk.html").write_text("<section id='desk'></section>", encoding="utf-8")
    (static / "index.html").write_text('<a href="desk.html">研究台</a>', encoding="utf-8")
    desk = SellerDesk(store=SellerStore(tmp_path / "seller"), quote=MockQuoteBackend())
    server = H5Server("127.0.0.1", 0, static_root=static, desk=desk)
    server.start_background()
    base = f"http://127.0.0.1:{server.port}"
    try:
        home = urlopen(f"{base}/", timeout=5).read().decode()
        assert "desk.html" in home
        _json(f"{base}/api/seller/scan", "POST", {"underlyings": "US.BIDU"})
        scanned = _json(f"{base}/api/seller/scan", "POST", {"underlyings": "nvidia"})
        assert scanned["watchlist"] == ["US.NVDA"]
        assert all(c["underlying"] == "US.NVDA" for c in scanned["cards"])
        filtered = _json(f"{base}/api/seller?q=nvidia")
        assert filtered["count"] >= 1
        assert all(c["underlying"] == "US.NVDA" for c in filtered["cards"])
        assert not any("BIDU" in c["underlying"] for c in filtered["cards"])
    finally:
        server.stop()


def test_vault_map_exposes_desk_ui():
    root = Path(__file__).resolve().parents[1]
    assert (root / "scripts" / "serve_h5.py").is_file()
    vault = Path(__file__).resolve().parents[2] / "docs" / "vault-map"
    home = (vault / "index.html").read_text(encoding="utf-8")
    desk = (vault / "desk.html").read_text(encoding="utf-8")
    assert 'href="desk.html"' in home
    assert 'href="chain.html"' in home
    assert 'href="chat.html"' in home
    assert 'id="desk"' not in home
    assert 'id="desk"' in desk
    assert "chat-launch" not in home
    assert "chat-launch" not in desk
    assert "#chat-panel" not in home
    nav = home.split("</nav>", 1)[0]
    assert "#roles" not in nav
    assert "#strategies" not in nav
    assert "#concepts" not in nav
    js = (vault / "desk.js").read_text(encoding="utf-8")
    assert "/api/seller/scan" in js
    assert "/api/seller/verdict" in js
    assert "/api/seller/monitor" in js
    assert "nvidia" in js.lower()
    assert 'verdict(card.id, "clear")' in js or "verdict(card.id, 'clear')" in js
