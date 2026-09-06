"""Seller-desk card schema (our names; research mids, no fees)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .payoff import StructureId

Verdict = Literal["adopt", "watch", "reject"]
CardStatus = Literal["signal", "tracked", "settled"]
FollowStatus = Literal["", "dry_run", "research_open", "sequential_submitted"]

WIKI_PATHS: dict[StructureId, str] = {
    "bull_put_spread": "wiki/strategies/Bull Put Spread (Credit Put Spread).md",
    "bear_call_spread": "wiki/strategies/Bear Call Spread (Credit Call Spread).md",
}


def card_id(
    underlying: str,
    expiry: str,
    structure_id: StructureId,
    short_strike: float,
    long_strike: float,
) -> str:
    exp = expiry[:10]
    return f"{underlying}-{exp}-{structure_id}-{short_strike:g}-{long_strike:g}"


@dataclass
class LegQuote:
    code: str
    side: str  # SELL | BUY
    option_type: str
    strike: float
    expiry: str
    bid: float
    ask: float
    last: float
    delta: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SellerCard:
    id: str
    underlying: str
    structure_id: StructureId
    wiki_path: str
    expiry: str
    spot: float
    dte: int
    short: LegQuote
    long: LegQuote
    credit: float
    width: float
    max_profit: float
    max_loss: float
    breakeven: float
    short_distance_pct: float
    passed: list[str] = field(default_factory=list)
    credit_kind: str = "conservative_bid_ask"
    verdict: Verdict | None = None
    status: CardStatus = "signal"
    follow_status: FollowStatus = ""
    leg_risk: str = ""
    mark_pnl: float | None = None
    mark_close_debit: float | None = None
    created_at: str = ""
    updated_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> SellerCard:
        data = dict(raw)
        data["short"] = LegQuote(**data["short"])
        data["long"] = LegQuote(**data["long"])
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})
