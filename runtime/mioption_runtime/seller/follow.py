"""Follow our local cards. Default dry-run; Futu SIMULATE has no combo options."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from ..futu.policy import PolicyError, TradeEnv, TradePolicy
from ..futu.trade import Leg, OrderRequest, TradeBackend
from .store import SellerStore

STOP_NAME = "STOP"


def stop_path(store: SellerStore) -> Path:
    return store.root / STOP_NAME


def stop_active(store: SellerStore) -> bool:
    return stop_path(store).is_file()


def follow_once(
    store: SellerStore,
    *,
    trade: TradeBackend | None = None,
    policy: TradePolicy | None = None,
    submit: bool = False,
    sequential: bool = False,
    whitelist: list[str] | None = None,
) -> dict[str, Any]:
    """Adopted cards only. Default: research_open, no broker order.

    `--submit --legs sequential` uses existing per-leg place() and tags
    `leg_risk: sequential`. Combo REAL is out of scope for v1.
    """
    policy = policy or TradePolicy()
    names = set(whitelist or [])
    if stop_active(store):
        return {"ok": False, "error": "stop_file", "path": str(stop_path(store)), "orders": []}

    adopted = [
        c
        for c in store.list_cards()
        if c.verdict == "adopt" and c.follow_status in ("", "research_open", "dry_run")
    ]
    reports: list[dict[str, Any]] = []
    for card in adopted:
        if names and card.underlying not in names:
            reports.append({"card_id": card.id, "skipped": True, "reason": "not_in_whitelist"})
            continue
        plan = {
            "card_id": card.id,
            "underlying": card.underlying,
            "structure_id": card.structure_id,
            "legs": [
                {
                    "code": card.short.code,
                    "side": "SELL",
                    "qty": 1,
                    "price": card.short.bid,
                    "limit_kind": "ask_line_is_short_bid",
                },
                {
                    "code": card.long.code,
                    "side": "BUY",
                    "qty": 1,
                    "price": card.long.ask,
                    "limit_kind": "long_ask",
                },
            ],
            "credit": card.credit,
            "env": policy.env.value,
            "combo": False,
            "note": "Futu SIMULATE does not support combo option orders",
        }
        if not submit:
            card.follow_status = "dry_run"
            card.status = "tracked"
            store.save_card(card)
            reports.append({"ok": True, "mode": "dry_run", "placed": False, **plan})
            continue

        if not sequential:
            card.follow_status = "research_open"
            card.status = "tracked"
            store.save_card(card)
            reports.append(
                {
                    "ok": True,
                    "mode": "research_open",
                    "placed": False,
                    "reason": "submit_without_sequential_marks_only",
                    **plan,
                }
            )
            continue

        if trade is None:
            reports.append({"ok": False, "card_id": card.id, "error": "no_trade_backend"})
            continue
        try:
            policy.authorize_open(notional=card.max_loss, naked_short=False)
        except PolicyError as exc:
            reports.append({"ok": False, "card_id": card.id, "error": exc.code, "message": exc.message})
            continue

        req = OrderRequest(
            underlying=card.underlying,
            structure_id=card.structure_id,
            env=TradeEnv.SIMULATE,
            notional=card.max_loss,
            naked_short=False,
            legs=[
                Leg(code=card.short.code, side="SELL", qty=1, price=card.short.bid, option_type=card.short.option_type, strike=card.short.strike, expiry=card.expiry),
                Leg(code=card.long.code, side="BUY", qty=1, price=card.long.ask, option_type=card.long.option_type, strike=card.long.strike, expiry=card.expiry),
            ],
        )
        result = trade.place(req)
        if result.ok:
            card.follow_status = "sequential_submitted"
            card.leg_risk = "sequential"
            card.status = "tracked"
            store.save_card(card)
            policy.note_order(time.time())
        reports.append({"ok": result.ok, "mode": "sequential", "placed": result.ok, "order": result.as_dict(), **plan})
    return {"ok": True, "count": len(reports), "orders": reports, "submit": submit, "sequential": sequential}
