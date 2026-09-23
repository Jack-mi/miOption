"""Facade used by MCP and CLIs."""

from __future__ import annotations

from datetime import date
from typing import Any, Iterable

from ..futu.policy import TradePolicy
from ..futu.quote import QuoteBackend, get_quote_backend
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
        self.params = params or ScanParams()
        self.monitor_params = monitor or MonitorParams()
        self.quote_store = quote_store

    def scan(self, underlyings: Iterable[str] | None = None, today: date | None = None) -> dict[str, Any]:
        with self.store.transaction():
            return scan_watchlist(
                self.quote,
                underlyings=underlyings,
                today=today,
                params=self.params,
                store=self.store,
                quote_store=self.quote_store,
            )

    def list_cards(self, status: str | None = None) -> dict[str, Any]:
        cards = self.store.list_cards(status=status)
        return {"count": len(cards), "cards": [c.as_dict() for c in cards]}

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
            "cards": [c.as_dict() for c in cards],
            "events": events[-80:],
            "place_order": False,
        }
