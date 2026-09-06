"""OIC-style credit-vertical math. Numbers come from quotes, not from OSM."""

from __future__ import annotations

from typing import Any, Literal

StructureId = Literal["bull_put_spread", "bear_call_spread"]


def mid(bid: float, ask: float, last: float = 0.0) -> float:
    if bid > 0 and ask > 0:
        return (bid + ask) / 2.0
    return last


def conservative_credit(
    *,
    short_bid: float,
    long_ask: float,
) -> float:
    """Sell the short at bid, buy the long at ask. Negative means not a credit."""
    return round(short_bid - long_ask, 4)


def credit_vertical_payoff(
    structure_id: StructureId,
    *,
    short_strike: float,
    long_strike: float,
    credit: float,
) -> dict[str, Any]:
    """Max profit / max loss / break-even at expiration for a 1x1 credit vertical.

    OIC: max gain is the net credit; max loss is width minus credit;
    bull-put BE is short strike minus credit; bear-call BE is short strike plus credit.
    """
    if structure_id == "bull_put_spread":
        width = round(short_strike - long_strike, 4)
        breakeven = round(short_strike - credit, 4)
    elif structure_id == "bear_call_spread":
        width = round(long_strike - short_strike, 4)
        breakeven = round(short_strike + credit, 4)
    else:
        raise ValueError(f"unsupported structure {structure_id}")
    if width <= 0:
        raise ValueError("protection strike is on the wrong side of the short")
    max_profit = round(credit * 100.0, 2)
    max_loss = round((width - credit) * 100.0, 2)
    return {
        "structure_id": structure_id,
        "width": width,
        "credit": credit,
        "max_profit": max_profit,
        "max_loss": max_loss,
        "breakeven": breakeven,
        "basis": "research_mid_or_conservative_credit",
    }


def close_debit(*, long_bid: float, short_ask: float) -> float:
    """Cost to buy back a credit spread: buy the short at ask, sell the long at bid."""
    return round(short_ask - long_bid, 4)


def settlement_intrinsic(
    structure_id: StructureId,
    *,
    short_strike: float,
    long_strike: float,
    spot: float,
) -> float:
    """Intrinsic value of the spread per share at expiration (0 .. width)."""
    if structure_id == "bull_put_spread":
        if spot >= short_strike:
            return 0.0
        if spot <= long_strike:
            return round(short_strike - long_strike, 4)
        return round(short_strike - spot, 4)
    if spot <= short_strike:
        return 0.0
    if spot >= long_strike:
        return round(long_strike - short_strike, 4)
    return round(spot - short_strike, 4)


def settlement_pnl(
    structure_id: StructureId,
    *,
    short_strike: float,
    long_strike: float,
    credit: float,
    spot: float,
) -> float:
    intrinsic = settlement_intrinsic(
        structure_id,
        short_strike=short_strike,
        long_strike=long_strike,
        spot=spot,
    )
    return round((credit - intrinsic) * 100.0, 2)
