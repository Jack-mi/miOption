"""Facade used by MCP and CLIs."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import sys
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from ..futu.policy import TradePolicy
from ..futu.quote import MockQuoteBackend, QuoteBackend, get_quote_backend
from ..futu.quote_store import QuoteStore
from ..futu.trade import TradeBackend
from .monitor import MonitorParams, apply_verdict, monitor_tick
from .scan import DEFAULT_WATCHLIST, ScanParams, resolve_underlyings, scan_watchlist
from .store import SellerStore, default_root


def default_store() -> SellerStore:
    return SellerStore(default_root())


class SellerDesk:
    def __init__(
        self,
        store: SellerStore | None = None,
        quote: QuoteBackend | None = None,
        trade: TradeBackend | None = None,
        policy: TradePolicy | None = None,
        params: ScanParams | None = None,
        monitor: MonitorParams | None = None,
        quote_store: QuoteStore | None = None,
    ):
        self.store = store or default_store()
        self.quote = quote if quote is not None else get_quote_backend()
        self.trade = trade
        self.policy = policy or TradePolicy()
        self.params = params
        self.monitor_params = monitor or MonitorParams()
        self.quote_store = quote_store

    def scan(self, underlyings: Iterable[str] | None = None, today: date | None = None) -> dict[str, Any]:
        repo_root = str(Path(__file__).resolve().parents[3])
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from signal_chain.agents import session
        from signal_chain.options.strategy_menu import apply_user_bias
        from signal_chain.risk.account_equity import read_account_equity
        from signal_chain.config import load_settings

        names = resolve_underlyings(underlyings)
        day = today or datetime.now(ZoneInfo("America/New_York")).date()
        settings = load_settings()
        live_account = read_account_equity("US", settings) if not isinstance(self.quote, MockQuoteBackend) else None
        evidence = {}
        for name in names:
            market = session.fresh_market(name, day)
            decision = session.get_decision(name, day)
            direction = apply_user_bias(decision.ensemble, decision.bias).direction.value if decision else ""
            evidence[name] = {
                "account": live_account,
                "closes": [(bar.trade_date, bar.close) for bar in market.snapshot.kline.bars] if market else [],
                "earnings": market.snapshot.earnings_date if market else None,
                "signal_ok": bool(decision and decision.risk.get("signal_gate", {}).get("approved", False)
                                  and abs(decision.ensemble.conviction) >= settings.risk["min_conviction"]
                                  and decision.ensemble.volatility_view != "rising"),
                "signal_direction": ("buy" if direction in {"buy", "strong_buy"}
                                     else "sell" if direction in {"sell", "strong_sell"} else None),
                "review_ok": bool(decision and decision.risk.get("review", {}).get("ok", False)),
                "config": settings.risk,
            }
        with self.store.transaction():
            return scan_watchlist(
                self.quote,
                underlyings=names,
                today=today,
                params=self.params,
                store=self.store,
                quote_store=self.quote_store,
                evidence=evidence,
            )

    def list_cards(self, status: str | None = None) -> dict[str, Any]:
        cards = self.store.list_cards(status=status)
        return {"count": len(cards), "cards": [self._historical_card(card) for card in cards]}

    @staticmethod
    def _historical_card(card) -> dict[str, Any]:
        payload = card.as_dict()
        if payload["tier"] != "禁做":
            payload["tier"] = "仅观察"
        payload["tier_reasons"] = [*payload["tier_reasons"], "历史卡片需重取盘口及决策证据"]
        return payload

    def verdict(self, card_id: str, verdict: str, note: str = "") -> dict[str, Any]:
        allowed = ("adopt", "watch", "reject", "clear")
        if verdict not in allowed:
            return {"ok": False, "error": "bad_verdict", "allowed": list(allowed)}
        with self.store.transaction():
            return apply_verdict(self.store, card_id, verdict, note=note)

    def monitor_tick(self, today: date | None = None) -> dict[str, Any]:
        with self.store.transaction():
            return monitor_tick(
                self.store,
                self.quote,
                today=today,
                params=self.monitor_params,
                quote_store=self.quote_store,
            )

    def snapshot(self, status: str | None = None, query: str | None = None) -> dict[str, Any]:
        cards = self.store.list_cards(status=status)
        wanted = resolve_underlyings(query) if query else []
        if query and wanted:
            allow = set(wanted)
            cards = [c for c in cards if c.underlying in allow]
        events = self.store.list_events()
        sources = sorted({card.quote_source for card in cards})
        quote_source = sources[0] if len(sources) == 1 else "mixed" if sources else (
            "mock" if type(self.quote).__name__ == "MockQuoteBackend" else "futu"
        )
        return {
            "ok": True,
            "service": "mioption-seller",
            "mock": quote_source == "mock",
            "quote_source": quote_source,
            "sources": sources,
            "watchlist": wanted or list(DEFAULT_WATCHLIST),
            "query": query or "",
            "count": len(cards),
            "cards": [self._historical_card(card) for card in cards],
            "events": events[-80:],
            "place_order": False,
        }
