"""Evaluate decision recipes against a context dict."""

from __future__ import annotations

from typing import Any

from .models import Condition


def _compare(op: str, left: Any, right: Any) -> bool:
    if op == "exists":
        return left is not None
    if left is None:
        return False
    if op == "gt":
        return left > right
    if op == "gte":
        return left >= right
    if op == "lt":
        return left < right
    if op == "lte":
        return left <= right
    if op == "eq":
        return left == right
    raise ValueError(f"unknown op {op}")


def resolve_path(ctx: dict[str, Any], name: str) -> Any:
    cur: Any = ctx
    for part in name.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def eval_condition(cond: Condition, ctx: dict[str, Any]) -> bool:
    left = resolve_path(ctx, cond.name)
    return _compare(cond.op, left, cond.value)


def eval_all(conditions: list[Condition], ctx: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    details = []
    ok = True
    for cond in conditions:
        passed = eval_condition(cond, ctx)
        details.append({"condition": cond.as_dict(), "passed": passed})
        if not passed:
            ok = False
    return ok, details
