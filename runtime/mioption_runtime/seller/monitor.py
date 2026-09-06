"""Mid-mark, protection/take-profit windows, settlement. Remind-only by default."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

from ..futu.quote import OptionContract, QuoteBackend
from .cards import SellerCard, Verdict
from .payoff import close_debit, settlement_pnl
from .scan import overlay_snapshot
from .store import SellerStore

GetQuotes = Callable[[list[str]], dict[str, dict[str, Any]]]


@dataclass
class MonitorParams:
    take_profit_credit_frac: float = 0.35
    protect_cost_vs_max_risk: float = 0.25
    extra_width: float = 5.0
    strike_tol: float = 0.26


def _quotes_from_backend(backend: QuoteBackend, codes: list[str]) -> dict[str, dict[str, Any]]:
    fn = getattr(backend, "snapshots", None)
    if callable(fn):
        return fn(codes)
    return {code: backend.snapshot(code) for code in codes}


def _leg_quote(backend: QuoteBackend, code: str, fallback_bid: float, fallback_ask: float) -> tuple[float, float]:
    snap = backend.snapshot(code)
    bid = float(snap.get("bid_price") or snap.get("bid") or fallback_bid or 0)
    ask = float(snap.get("ask_price") or snap.get("ask") or fallback_ask or 0)
    return bid, ask


def mark_card(card: SellerCard, backend: QuoteBackend) -> SellerCard:
    short_bid, short_ask = _leg_quote(backend, card.short.code, card.short.bid, card.short.ask)
    long_bid, long_ask = _leg_quote(backend, card.long.code, card.long.bid, card.long.ask)
    debit = close_debit(long_bid=long_bid, short_ask=short_ask)
    card.mark_close_debit = debit
    card.mark_pnl = round((card.credit - debit) * 100.0, 2)
    card.short.bid, card.short.ask = short_bid, short_ask
    card.long.bid, card.long.ask = long_bid, long_ask
    return card


def take_profit_hit(card: SellerCard, params: MonitorParams) -> bool:
    if card.mark_close_debit is None or card.credit <= 0:
        return False
    return card.mark_close_debit <= card.credit * params.take_profit_credit_frac


def _protection_candidate(
    card: SellerCard,
    chain: list[OptionContract],
    params: MonitorParams,
) -> OptionContract | None:
    if card.structure_id == "bull_put_spread":
        target = card.long.strike - params.extra_width
        opt = "PUT"
    else:
        target = card.long.strike + params.extra_width
        opt = "CALL"
    exp = card.expiry[:10]
    for c in chain:
        if c.option_type != opt:
            continue
        if str(c.expiry)[:10] != exp:
            continue
        if abs(c.strike - target) <= params.strike_tol:
            return c
    return None


def protection_hit(
    card: SellerCard,
    extra: OptionContract,
    params: MonitorParams,
) -> bool:
    if extra.ask <= 0 or card.max_loss <= 0:
        return False
    cost = extra.ask * 100.0
    return cost <= card.max_loss * params.protect_cost_vs_max_risk


def settle_card(card: SellerCard, spot: float) -> dict[str, Any]:
    pnl = settlement_pnl(
        card.structure_id,
        short_strike=card.short.strike,
        long_strike=card.long.strike,
        credit=card.credit,
        spot=spot,
    )
    card.status = "settled"
    card.mark_pnl = pnl
    return {
        "kind": "settle",
        "card_id": card.id,
        "spot": spot,
        "pnl": pnl,
        "planned": False,
    }


def apply_verdict(store: SellerStore, card_id: str, verdict: Verdict, note: str = "") -> dict[str, Any]:
    card = store.get_card(card_id)
    if card is None:
        return {"ok": False, "error": "unknown_card", "card_id": card_id}
    card.verdict = verdict
    if verdict == "adopt":
        card.status = "tracked"
        if not card.follow_status:
            card.follow_status = "research_open"
    store.save_card(card)
    mark = store.save_mark(card_id, verdict, note=note)
    return {"ok": True, "card": card.as_dict(), "mark": mark}


def monitor_tick(
    store: SellerStore,
    backend: QuoteBackend,
    *,
    today: date | None = None,
    params: MonitorParams | None = None,
    chain_for: Callable[[str], list[OptionContract]] | None = None,
) -> dict[str, Any]:
    """Mark tracked/adopted cards. Emits events; never places orders."""
    params = params or MonitorParams()
    today = today or date.today()
    events: list[dict[str, Any]] = []
    tracked = [
        c
        for c in store.list_cards()
        if c.status != "settled" and (c.verdict == "adopt" or c.status == "tracked")
    ]
    for card in tracked:
        exp = date.fromisoformat(card.expiry[:10])
        if today >= exp:
            snap = backend.snapshot(card.underlying)
            spot = float(snap.get("last_price") or snap.get("last") or card.spot)
            ev = settle_card(card, spot)
            store.save_card(card)
            events.append(store.append_event(ev))
            continue
        mark_card(card, backend)
        store.save_card(card)
        seen = {(e.get("kind") or "") for e in store.list_events(card.id)}
        if take_profit_hit(card, params) and "take_profit" not in seen:
            events.append(
                store.append_event(
                    {
                        "kind": "take_profit",
                        "card_id": card.id,
                        "close_debit": card.mark_close_debit,
                        "credit": card.credit,
                        "mark_pnl": card.mark_pnl,
                        "place_order": False,
                    }
                )
            )
        chain = chain_for(card.underlying) if chain_for else backend.option_chain(card.underlying)
        extra = _protection_candidate(card, chain, params)
        if extra is not None:
            snap = backend.snapshot(extra.code)
            extra = overlay_snapshot(extra, snap) if snap else extra
            if protection_hit(card, extra, params) and "protect" not in seen:
                events.append(
                    store.append_event(
                        {
                            "kind": "protect",
                            "card_id": card.id,
                            "extra_code": extra.code,
                            "extra_strike": extra.strike,
                            "extra_ask": extra.ask,
                            "place_order": False,
                            "planned_forced_protect": True,
                            "planned_roll": True,
                        }
                    )
                )
    return {
        "ok": True,
        "tracked": len(tracked),
        "events": events,
        "as_of": today.isoformat(),
        "place_order": False,
    }
