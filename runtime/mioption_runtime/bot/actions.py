"""Map bot Actions onto Futu trade tools."""

from __future__ import annotations

from typing import Any

from ..futu.policy import TradeEnv
from ..futu.trade import Leg, OrderRequest, TradeBackend
from .models import Action, ExitRules


def build_order(action: Action, env: TradeEnv = TradeEnv.SIMULATE) -> OrderRequest:
    legs = [
        Leg(
            code=str(leg["code"]),
            side=str(leg["side"]).upper(),
            qty=float(leg.get("qty", 1)),
            price=float(leg["price"]) if leg.get("price") is not None else None,
            option_type=leg.get("option_type"),
            strike=leg.get("strike"),
            expiry=leg.get("expiry"),
        )
        for leg in action.legs
    ]
    return OrderRequest(
        underlying=action.underlying or "",
        legs=legs,
        structure_id=action.structure_id,
        env=env,
        notional=action.notional,
        naked_short=action.naked_short,
    )


def run_action(
    action: Action,
    trade: TradeBackend,
    *,
    managed: dict[str, Any],
    env: TradeEnv = TradeEnv.SIMULATE,
) -> dict[str, Any]:
    if action.kind == "tag":
        managed.setdefault("tags", []).append(action.tag)
        return {"ok": True, "kind": "tag", "tag": action.tag}

    if action.kind == "update_exit_rules":
        pid = action.position_id
        if not pid or pid not in managed.get("positions", {}):
            return {"ok": False, "kind": "update_exit_rules", "message": "unknown position"}
        rules = action.exit_rules or ExitRules()
        managed["positions"][pid]["exit_rules"] = rules.as_dict()
        return {"ok": True, "kind": "update_exit_rules", "position_id": pid, "exit_rules": rules.as_dict()}

    if action.kind == "close_position":
        pid = action.position_id
        positions = managed.setdefault("positions", {})
        if not pid or pid not in positions:
            return {"ok": False, "kind": "close_position", "message": "unknown position"}
        pos = positions[pid]
        # Flatten by reversing sides on stored fills
        close_legs = []
        for fill in pos.get("legs", []):
            close_legs.append(
                {
                    "code": fill["code"],
                    "side": "SELL" if fill["side"] == "BUY" else "BUY",
                    "qty": fill["qty"],
                    "price": fill.get("price"),
                }
            )
        close_action = Action(
            kind="open_position",
            underlying=pos.get("underlying"),
            structure_id=pos.get("structure_id"),
            legs=close_legs,
            notional=0.0,
        )
        order = build_order(close_action, env=env)
        result = trade.place(order)
        if result.ok:
            pos["status"] = "closed"
            trade.policy.controls.record_close(pos.get("notional", 0.0))
        out = result.as_dict()
        out["kind"] = "close_position"
        out["position_id"] = pid
        return out

    if action.kind == "open_position":
        order = build_order(action, env=env)
        result = trade.place(order)
        out = result.as_dict()
        out["kind"] = "open_position"
        if result.ok:
            pid = result.order_id
            managed.setdefault("positions", {})[pid] = {
                "position_id": pid,
                "underlying": action.underlying,
                "structure_id": action.structure_id,
                "legs": result.fills,
                "notional": action.notional,
                "status": "open",
                "exit_rules": (action.exit_rules or ExitRules()).as_dict(),
                "pnl_pct": 0.0,
                "dte": None,
            }
            out["position_id"] = pid
        return out

    return {"ok": False, "kind": action.kind, "message": "unknown action"}
