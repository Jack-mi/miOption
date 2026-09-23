from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from fastmcp import Client

from mioption_runtime.agent.stdio_mcp import build_mcp
from mioption_runtime.agent.tool_handlers import ToolRuntime
from mioption_runtime.agent.wiki import wiki_page, wiki_query
from mioption_runtime.futu.quote import MockQuoteBackend, mock_underlying_pack
from mioption_runtime.futu.quote_store import QuoteStore
from mioption_runtime.ingress.h5 import H5Server
from mioption_runtime.seller.desk import SellerDesk
from mioption_runtime.seller.follow import follow_once
from mioption_runtime.seller.store import SellerStore


@pytest.fixture
def research(tmp_path, monkeypatch):
    monkeypatch.setenv("MIOPTION_FUTU_MOCK", "1")
    monkeypatch.setenv("MIOPTION_SELLER_DIR", str(tmp_path / "seller"))
    monkeypatch.setenv("MIOPTION_QUOTES_DB", str(tmp_path / "quotes.sqlite"))
    quote_store = QuoteStore()
    desk = SellerDesk(quote=MockQuoteBackend(), quote_store=quote_store)
    server = H5Server("127.0.0.1", 0, desk=desk, quote_store=quote_store)
    server.start_background()
    yield server, desk, quote_store
    server.stop()


def request(server, path, payload=None, headers=None):
    query = Request(
        f"http://127.0.0.1:{server.port}{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    with urlopen(query, timeout=10) as response:
        return json.load(response)


def test_research_loop_pull_scan_adopt_follow_monitor_reload(research):
    server, desk, quote_store = research
    for page in ("index.html", "chain.html", "desk.html", "chat.html"):
        with urlopen(f"http://127.0.0.1:{server.port}/{page}", timeout=5) as response:
            assert response.status == 200
    pulled = request(server, "/api/chain/pull", {"underlyings": "BIDU", "days": 60})
    assert pulled["source"] == "mock"
    assert pulled["count"] == 10
    assert pulled["stale"] is False
    scanned = request(server, "/api/seller/scan", {"underlyings": "BIDU"})
    assert scanned["mock"] is True
    assert {card["structure_id"] for card in scanned["cards"]} == {"bull_put_spread", "bear_call_spread"}
    card = scanned["cards"][0]
    assert request(server, "/api/seller/verdict", {"card_id": card["id"], "verdict": "adopt"})["ok"]
    followed = follow_once(desk.store)
    assert followed["orders"][0]["placed"] is False
    pack = mock_underlying_pack("US.BIDU")
    for contract in pack["options"]:
        if contract["code"] == card["short"]["code"]:
            contract.update(bid=0.10, ask=0.12, last=0.11)
        elif contract["code"] == card["long"]["code"]:
            contract.update(bid=0.08, ask=0.10, last=0.09)
    quote_store.replace_current(pack)
    monitored = request(server, "/api/seller/monitor", {})
    assert monitored["ok"] is True
    assert monitored["place_order"] is False
    assert any(event["kind"] == "take_profit" for event in monitored["events"])
    request(server, "/api/seller/scan", {"underlyings": "BIDU"})
    reopened = SellerStore(desk.store.root)
    saved = reopened.get_card(card["id"])
    assert saved.status == "tracked"
    assert saved.credit == card["credit"]
    assert saved.follow_status == "dry_run"
    assert saved.created_at == card["created_at"]
    assert reopened.list_events(card["id"])
    assert request(server, "/api/seller/monitor", {})["events"] == []
    page = wiki_page(card["wiki_path"])
    assert "## Legs" in page["content"]


def test_stale_snapshot_rejected_without_deleting_cards(research):
    server, desk, quote_store = research
    request(server, "/api/chain/pull", {"underlyings": "BIDU"})
    scanned = desk.scan(["US.BIDU"])
    before = {card["id"] for card in scanned["cards"]}
    desk.verdict(scanned["cards"][0]["id"], "adopt")
    pack = mock_underlying_pack("US.BIDU")
    pack["pulled_at"] = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
    quote_store.replace_current(pack)
    assert desk.scan(["US.BIDU"])["errors"]
    monitored = desk.monitor_tick()
    assert monitored["ok"] is False
    assert "quote_snapshot_stale" in str(monitored["errors"])
    assert {card.id for card in desk.store.list_cards()} == before


def test_source_mismatch_never_marks_live_card_with_mock(research):
    server, desk, quote_store = research
    request(server, "/api/chain/pull", {"underlyings": "BIDU"})
    card = desk.scan(["US.BIDU"])["cards"][0]
    saved = desk.store.get_card(card["id"])
    saved.quote_source = "futu"
    desk.store.save_card(saved)
    desk.verdict(saved.id, "adopt")
    monitored = desk.monitor_tick()
    assert "quote_source_mismatch" in str(monitored["errors"])
    assert desk.store.get_card(saved.id).mark_pnl is None


def test_expiry_requires_confirmation_not_current_spot_settlement(research):
    server, desk, quote_store = research
    request(server, "/api/chain/pull", {"underlyings": "BIDU"})
    card = desk.scan(["US.BIDU"])["cards"][0]
    desk.verdict(card["id"], "adopt")
    tomorrow = date.fromisoformat(card["expiry"]) + timedelta(days=1)
    monitored = desk.monitor_tick(today=tomorrow)
    assert monitored["events"][0]["kind"] == "expiry_review"
    saved = desk.store.get_card(card["id"])
    assert saved.status == "tracked"
    assert saved.mark_pnl is None
    assert desk.monitor_tick(today=tomorrow)["events"] == []


def test_cross_origin_writes_and_path_traversal_blocked(research, tmp_path):
    server, desk, quote_store = research
    with pytest.raises(HTTPError) as blocked:
        request(server, "/api/seller/scan", {"underlyings": "BIDU"}, {"Origin": "https://untrusted.invalid"})
    assert blocked.value.code == 403
    with pytest.raises(ValueError):
        desk.store.get_card("../../outside")
    with pytest.raises(ValueError):
        wiki_page("../README.md")
    with pytest.raises(HTTPError) as traversal:
        request(server, "/%2e%2e/README.md")
    assert traversal.value.code == 403
    with pytest.raises(HTTPError) as invalid:
        request(server, "/api/chain/pull", {"underlyings": "BIDU", "days": 9999})
    assert invalid.value.code == 400
    with pytest.raises(HTTPError) as rebound:
        request(server, "/api/health", headers={"Host": "attacker.invalid"})
    assert rebound.value.code == 403
    with pytest.raises(HTTPError) as invalid_symbol:
        request(server, "/api/chain/pull", {"underlyings": "../../outside"})
    assert invalid_symbol.value.code == 400


def test_events_do_not_overwrite_same_second(research):
    server, desk, quote_store = research
    for card_id in ("first", "second"):
        desk.store.append_event({"kind": "take_profit", "card_id": card_id, "at": "2026-09-20T00:00:00Z"})
    assert len(desk.store.list_events()) == 2


async def test_research_mcp_excludes_orders_and_blocks_dispatch(research, monkeypatch):
    monkeypatch.setenv("MIOPTION_RESEARCH_ONLY", "1")
    runtime = ToolRuntime()
    async with Client(build_mcp(runtime)) as client:
        names = {tool.name for tool in await client.list_tools()}
        assert "wiki_query" in names
        assert "futu_place_option_order" not in names
        assert "bot_run_automation" not in names
    for name in ("futu_place_option_order", "bot_run_automation"):
        assert runtime.dispatch(name, {})["error"] == "research_only"


def test_wiki_query_returns_citable_content():
    result = wiki_query("bull put spread", top=1)
    assert "Bull Put Spread" in result["candidates"][0]["page_path"]
    assert "Maximum loss" in result["candidates"][0]["content"]


def test_mcp_chain_uses_same_store_as_h5(research):
    server, desk, quote_store = research
    runtime = ToolRuntime()
    quoted = runtime.dispatch("futu_quote_chain", {"underlying": "BIDU"})
    assert quoted["source"] == "mock"
    assert quoted["count"] == 10
    assert quoted["truncated"] is False
    page = request(server, "/api/chain?q=BIDU")
    assert page["pulled_at"] == quoted["pulled_at"]
    assert page["count"] == quoted["count"]
    assert page["contracts"] == quoted["contracts"]
    assert runtime.dispatch("seller_scan", {"underlyings": "BIDU"})["count"] >= 2


def test_archive_rebuild_uses_frozen_matching_index():
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/build_knowledge.py", "--check"],
        cwd=root, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["strategies"] == 22


def test_default_storage_separates_mock_and_live(monkeypatch):
    from mioption_runtime.futu.quote_store import default_db_path
    from mioption_runtime.seller.store import default_root

    monkeypatch.delenv("MIOPTION_SELLER_DIR", raising=False)
    monkeypatch.delenv("MIOPTION_QUOTES_DB", raising=False)
    monkeypatch.setenv("MIOPTION_FUTU_MOCK", "1")
    mock_paths = default_db_path(), default_root()
    monkeypatch.setenv("MIOPTION_FUTU_MOCK", "0")
    live_paths = default_db_path(), default_root()
    assert all("mock" in str(path) for path in mock_paths)
    assert all("live" in str(path) for path in live_paths)
    assert mock_paths != live_paths


def test_launcher_starts_and_stops_without_leaving_listener(tmp_path):
    root = Path(__file__).resolve().parents[2]
    log_path = tmp_path / "server.log"
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with log_path.open("w") as log:
        process = subprocess.Popen(
            [sys.executable, "runtime/scripts/serve_h5.py", "--mode", "mock", "--port", str(port),
             "--data-dir", str(tmp_path / "state")],
            cwd=root, stdout=log, stderr=log, env={**os.environ},
        )
        try:
            deadline = time.monotonic() + 10
            while "READY" not in log_path.read_text():
                assert process.poll() is None, log_path.read_text()
                assert time.monotonic() < deadline, log_path.read_text()
                time.sleep(0.05)
            with urlopen(f"http://127.0.0.1:{port}/api/health", timeout=5) as response:
                health = json.load(response)
            assert health["service"] == "mioption-h5"
            assert health["mock"] is True
        finally:
            process.terminate()
            process.wait(timeout=10)
    assert process.returncode == 0
    with socket.socket() as probe:
        assert probe.connect_ex(("127.0.0.1", port)) != 0
