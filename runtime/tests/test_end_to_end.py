"""Desk + MCP end to end: mock quotes -> scan -> adopt -> follow -> monitor -> reload.

No HTTP layer: the browser workbench and its API are retired.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from fastmcp import Client

from mioption_runtime.agent.stdio_mcp import build_mcp
from mioption_runtime.agent.tool_handlers import ToolRuntime
from mioption_runtime.agent.wiki import wiki_page, wiki_query
from mioption_runtime.futu.quote import MockQuoteBackend, mock_underlying_pack
from mioption_runtime.futu.quote_store import QuoteStore
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
    quote_store.replace_current(mock_underlying_pack("US.BIDU"))
    yield desk, quote_store


def test_research_loop_scan_adopt_follow_monitor_reload(research):
    desk, quote_store = research
    scanned = desk.scan(["US.BIDU"])
    assert {card["structure_id"] for card in scanned["cards"]} == {"bull_put_spread", "bear_call_spread"}
    card = scanned["cards"][0]
    assert desk.verdict(card["id"], "adopt")["ok"]
    followed = follow_once(desk.store)
    assert followed["orders"][0]["placed"] is False
    pack = mock_underlying_pack("US.BIDU")
    for contract in pack["options"]:
        if contract["code"] == card["short"]["code"]:
            contract.update(bid=0.10, ask=0.12, last=0.11)
        elif contract["code"] == card["long"]["code"]:
            contract.update(bid=0.08, ask=0.10, last=0.09)
    quote_store.replace_current(pack)
    monitored = desk.monitor_tick()
    assert monitored["ok"] is True
    assert monitored["place_order"] is False
    assert any(event["kind"] == "take_profit" for event in monitored["events"])
    desk.scan(["US.BIDU"])
    reopened = SellerStore(desk.store.root)
    saved = reopened.get_card(card["id"])
    assert saved.status == "tracked"
    assert saved.credit == card["credit"]
    assert saved.follow_status == "dry_run"
    assert saved.created_at == card["created_at"]
    assert reopened.list_events(card["id"])
    assert desk.monitor_tick()["events"] == []
    page = wiki_page(card["wiki_path"])
    assert "## Legs" in page["content"]


def test_stale_snapshot_rejected_without_deleting_cards(research):
    desk, quote_store = research
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
    desk, quote_store = research
    card = desk.scan(["US.BIDU"])["cards"][0]
    saved = desk.store.get_card(card["id"])
    saved.quote_source = "futu"
    desk.store.save_card(saved)
    desk.verdict(saved.id, "adopt")
    monitored = desk.monitor_tick()
    assert "quote_source_mismatch" in str(monitored["errors"])
    assert desk.store.get_card(saved.id).mark_pnl is None


def test_expiry_requires_confirmation_not_current_spot_settlement(research):
    desk, quote_store = research
    card = desk.scan(["US.BIDU"])["cards"][0]
    desk.verdict(card["id"], "adopt")
    tomorrow = date.fromisoformat(card["expiry"]) + timedelta(days=1)
    monitored = desk.monitor_tick(today=tomorrow)
    assert monitored["events"][0]["kind"] == "expiry_review"
    saved = desk.store.get_card(card["id"])
    assert saved.status == "tracked"
    assert saved.mark_pnl is None
    assert desk.monitor_tick(today=tomorrow)["events"] == []


def test_events_do_not_overwrite_same_second(research):
    desk, _quote_store = research
    for card_id in ("first", "second"):
        desk.store.append_event({"kind": "take_profit", "card_id": card_id, "at": "2026-09-20T00:00:00Z"})
    assert len(desk.store.list_events()) == 2


async def test_research_mcp_excludes_orders_and_blocks_dispatch(monkeypatch):
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


def test_mcp_chain_reads_and_fills_the_desk_store(research):
    desk, quote_store = research
    runtime = ToolRuntime()
    quoted = runtime.dispatch("futu_quote_chain", {"underlying": "BIDU"})
    assert quoted["source"] == "mock"
    assert quoted["count"] == 10
    assert quoted["truncated"] is False
    stored = quote_store.current("US.BIDU")
    assert stored["pulled_at"] == quoted["pulled_at"]
    assert [c["code"] for c in quoted["contracts"]] == [c["code"] for c in stored["contracts"]]
    assert runtime.dispatch("seller_scan", {"underlyings": "BIDU"})["count"] >= 2


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
