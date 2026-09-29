"""Follow our local cards. Default dry-run; Futu SIMULATE has no combo options."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..futu.policy import TradePolicy
from ..futu.trade import TradeBackend
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
    """Adopted cards only; research dry-run, never broker submission."""
    policy = policy or TradePolicy()
    names = set(whitelist or [])
    if stop_active(store):
        return {"ok": False, "error": "stop_file", "path": str(stop_path(store)), "orders": []}
    if submit:
        return {"ok": False, "error": "research_only_no_submission", "orders": []}

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
        card.follow_status = "dry_run"
        card.status = "tracked"
        store.save_card(card)
        reports.append({"ok": True, "mode": "dry_run", "placed": False, **plan})
    return {"ok": True, "count": len(reports), "orders": reports, "submit": submit, "sequential": sequential}
