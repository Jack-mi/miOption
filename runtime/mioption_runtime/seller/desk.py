"""Facade used by MCP and CLIs."""

from __future__ import annotations

from datetime import date
from typing import Any, Iterable

from ..futu.policy import TradePolicy
from ..futu.quote import QuoteBackend, get_quote_backend
from ..futu.trade import TradeBackend
from .cards import Verdict
from .monitor import MonitorParams, apply_verdict, monitor_tick
from .scan import ScanParams, scan_watchlist
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
    ):
        self.store = store or default_store()
        self.quote = quote if quote is not None else get_quote_backend()
        self.trade = trade
        self.policy = policy or TradePolicy()
        self.params = params or ScanParams()
        self.monitor_params = monitor or MonitorParams()

    def scan(self, underlyings: Iterable[str] | None = None, today: date | None = None) -> dict[str, Any]:
        return scan_watchlist(
            self.quote,
            underlyings=underlyings,
            today=today,
            params=self.params,
            store=self.store,
        )

    def list_cards(self, status: str | None = None) -> dict[str, Any]:
        cards = self.store.list_cards(status=status)
        return {"count": len(cards), "cards": [c.as_dict() for c in cards]}

    def verdict(self, card_id: str, verdict: str, note: str = "") -> dict[str, Any]:
        allowed: tuple[Verdict, ...] = ("adopt", "watch", "reject")
        if verdict not in allowed:
            return {"ok": False, "error": "bad_verdict", "allowed": list(allowed)}
        return apply_verdict(self.store, card_id, verdict, note=note)  # type: ignore[arg-type]

    def monitor_tick(self, today: date | None = None) -> dict[str, Any]:
        return monitor_tick(
            self.store,
            self.quote,
            today=today,
            params=self.monitor_params,
        )
