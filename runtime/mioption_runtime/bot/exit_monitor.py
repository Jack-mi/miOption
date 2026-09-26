"""Exit-rules monitor: evaluate in-process; close only when criteria hit."""

from __future__ import annotations

from typing import Any, Callable

from ..futu.policy import TradeEnv
from ..futu.trade import TradeBackend
from .actions import run_action
from .models import Action, ExitRules


def should_exit(exit_rules: dict[str, Any] | ExitRules, position: dict[str, Any]) -> tuple[bool, str]:
    rules = exit_rules if isinstance(exit_rules, dict) else exit_rules.as_dict()
    if not rules.get("enabled", True):
        return False, "disabled"
    pnl = position.get("pnl_pct")
    if pnl is not None and rules.get("profit_take_pct") is not None:
        if pnl >= float(rules["profit_take_pct"]):
            return True, "profit_take_pct"
    if pnl is not None and rules.get("stop_loss_pct") is not None:
        if pnl <= float(rules["stop_loss_pct"]):
            return True, "stop_loss_pct"
    dte = position.get("dte")
    max_dte = rules.get("max_dte_remaining")
    if dte is not None and max_dte is not None and dte <= int(max_dte):
        return True, "max_dte_remaining"
    return False, ""


def tick(
    managed: dict[str, Any],
    trade: TradeBackend,
    *,
    env: TradeEnv = TradeEnv.SIMULATE,
    mark_pnl: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    """One monitor pass. Does not place resting exchange stops."""
    events: list[dict[str, Any]] = []
    for pid, pos in list(managed.get("positions", {}).items()):
        if pos.get("status") != "open":
            continue
        if mark_pnl:
            mark_pnl(pos)
        hit, reason = should_exit(pos.get("exit_rules") or {}, pos)
        if not hit:
            continue
        result = run_action(
            Action(kind="close_position", position_id=pid),
            trade,
            managed=managed,
            env=env,
        )
        events.append({"position_id": pid, "reason": reason, "result": result})
    return events
