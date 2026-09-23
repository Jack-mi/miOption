"""SDK-agnostic tool handlers. Futu/bot stay importable without Claude or Codex."""

from __future__ import annotations

import json
import os
from typing import Any

from ..bot.engine import BotEngine, demo_automation
from ..futu.opend import probe_permissions
from ..futu.policy import TradeEnv, TradePolicy
from ..futu.quote import mock_underlying_pack, pull_underlying_pack
from ..futu.quote_store import QuoteStore
from ..futu.trade import Leg, OrderRequest, get_trade_backend
from ..seller.desk import SellerDesk
from ..seller.scan import resolve_symbol
from .wiki import wiki_query

TOOL_DEFS: list[dict[str, Any]] = [
    {
        "name": "wiki_query",
        "description": (
            "Read-only Obsidian vault retrieval (knowledge/wiki). Use for strategy "
            "meaning and published P/L. Do not invent numbers. Skip wiki/meta pages "
            "for payoff evidence."
        ),
        "readOnlyHint": True,
        "destructiveHint": False,
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top": {"type": "number"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "futu_probe",
        "description": "Probe OpenD connectivity and high-level account permissions (no orders).",
        "readOnlyHint": True,
        "destructiveHint": False,
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "futu_quote_chain",
        "description": "Fetch an option chain for an underlying (mock unless MIOPTION_FUTU_MOCK=0).",
        "readOnlyHint": True,
        "destructiveHint": False,
        "inputSchema": {
            "type": "object",
            "properties": {
                "underlying": {"type": "string"},
                "expiry": {"type": "string"},
            },
            "required": ["underlying"],
        },
    },
    {
        "name": "futu_place_option_order",
        "description": "Place an option order. Default env=SIMULATE. REAL requires policy unlock.",
        "readOnlyHint": False,
        "destructiveHint": True,
        "inputSchema": {
            "type": "object",
            "properties": {
                "underlying": {"type": "string"},
                "code": {"type": "string"},
                "side": {"type": "string"},
                "qty": {"type": "number"},
                "price": {"type": "number"},
                "env": {"type": "string"},
                "structure_id": {"type": "string"},
                "naked_short": {"type": "boolean"},
            },
            "required": ["underlying", "code"],
        },
    },
    {
        "name": "bot_run_automation",
        "description": "Run bot automations for a trigger kind (webhook/agent/button/schedule).",
        "readOnlyHint": False,
        "destructiveHint": True,
        "inputSchema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string"},
                "webhook_id": {"type": "string"},
                "context_json": {"type": "string"},
            },
        },
    },
    {
        "name": "seller_scan",
        "description": "Scan a watchlist on OpenD for bull-put / bear-call credit cards. Does not call OSM.",
        "readOnlyHint": True,
        "destructiveHint": False,
        "inputSchema": {
            "type": "object",
            "properties": {"underlyings": {"type": "string"}},
        },
    },
    {
        "name": "seller_list_cards",
        "description": "List local seller-desk cards (signals / tracked / settled).",
        "readOnlyHint": True,
        "destructiveHint": False,
        "inputSchema": {
            "type": "object",
            "properties": {"status": {"type": "string"}},
        },
    },
    {
        "name": "seller_verdict",
        "description": "Record adopt/watch/reject on a card. Does not place an order.",
        "readOnlyHint": False,
        "destructiveHint": False,
        "inputSchema": {
            "type": "object",
            "properties": {
                "card_id": {"type": "string"},
                "verdict": {"type": "string"},
                "note": {"type": "string"},
            },
            "required": ["card_id", "verdict"],
        },
    },
    {
        "name": "seller_monitor_tick",
        "description": "Mark tracked cards; emit protect/take-profit/settle events. Remind-only.",
        "readOnlyHint": False,
        "destructiveHint": False,
        "inputSchema": {"type": "object", "properties": {}},
    },
]


class ToolRuntime:
    def __init__(
        self,
        policy: TradePolicy | None = None,
        engine: BotEngine | None = None,
    ):
        self.policy = policy or TradePolicy()
        self.engine = engine or BotEngine(
            automations=[demo_automation()],
            policy=self.policy,
            prefer_mock=True,
        )
        self.seller = SellerDesk(policy=self.policy, quote_store=QuoteStore())

    def dispatch(self, name: str, args: dict[str, Any] | None) -> dict[str, Any]:
        args = args or {}
        if os.environ.get("MIOPTION_RESEARCH_ONLY") == "1" and name in ("futu_place_option_order", "bot_run_automation"):
            return {"ok": False, "error": "research_only", "place_order": False}
        if name == "wiki_query":
            return wiki_query(str(args.get("query") or ""), top=int(args.get("top") or 5))
        if name == "futu_probe":
            return probe_permissions()
        if name == "futu_quote_chain":
            underlying = resolve_symbol(str(args["underlying"]))
            if not underlying:
                return {"ok": False, "error": "invalid_underlying", "contracts": []}
            store = self.seller.quote_store
            pack = store.current(underlying)
            source = "mock" if os.environ.get("MIOPTION_FUTU_MOCK", "1") == "1" else "futu"
            if pack and pack["source"] != source:
                return {"ok": False, "error": "quote_source_mismatch", "contracts": []}
            if pack is None or pack.get("stale"):
                pull = mock_underlying_pack if source == "mock" else pull_underlying_pack
                store.replace_current(pull(underlying))
                pack = store.current(underlying)
            contracts = pack["contracts"]
            if args.get("expiry"):
                contracts = [contract for contract in contracts if contract["expiry"] == args["expiry"]]
            return {
                "ok": True, "underlying": underlying, "source": pack["source"],
                "pulled_at": pack["pulled_at"], "stale": pack["stale"],
                "count": len(contracts), "contracts": contracts[:100],
                "truncated": len(contracts) > 100, "expiries": pack["expiries"],
                "place_order": False,
            }
        if name == "futu_place_option_order":
            env = TradeEnv(str(args.get("env") or "SIMULATE").upper())
            trade = get_trade_backend(policy=self.policy)
            req = OrderRequest(
                underlying=str(args["underlying"]),
                legs=[
                    Leg(
                        code=str(args["code"]),
                        side=str(args.get("side") or "BUY").upper(),
                        qty=float(args.get("qty") or 1),
                        price=float(args["price"]) if args.get("price") is not None else None,
                    )
                ],
                structure_id=args.get("structure_id"),
                env=env,
                naked_short=bool(args.get("naked_short") or False),
                notional=float(args.get("price") or 0) * 100 * float(args.get("qty") or 1),
            )
            return trade.place(req).as_dict()
        if name == "bot_run_automation":
            ctx: dict[str, Any] = {}
            if args.get("context_json"):
                ctx = json.loads(str(args["context_json"]))
            return self.engine.run(
                str(args.get("kind") or "agent"),
                webhook_id=args.get("webhook_id"),
                context=ctx,
            )
        if name == "seller_scan":
            raw = args.get("underlyings")
            names = [p.strip() for p in str(raw).split(",") if p.strip()] if raw else None
            return self.seller.scan(names)
        if name == "seller_list_cards":
            status = args.get("status") or None
            return self.seller.list_cards(status=status)
        if name == "seller_verdict":
            return self.seller.verdict(
                str(args["card_id"]),
                str(args["verdict"]),
                note=str(args.get("note") or ""),
            )
        if name == "seller_monitor_tick":
            return self.seller.monitor_tick()
        raise KeyError(name)


def text_result(payload: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": str(payload)}]}
