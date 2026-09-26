"""Deterministic PreToolUse gates (cannot be talked around by the model)."""

from __future__ import annotations

from typing import Any

from ..futu.policy import TradeEnv, TradePolicy


REAL_TOOL_MARKERS = (
    "futu_place_option_order",
    "bot_run_automation",
    "futu_cancel_order",
)


def pre_tool_use_gate(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: Any,
    *,
    policy: TradePolicy,
) -> dict[str, Any]:
    """Return Claude Agent SDK hook output; deny REAL or locked tools."""
    del tool_use_id, context
    tool_name = str(input_data.get("tool_name") or "")
    tool_input = input_data.get("tool_input") or {}
    env = str(tool_input.get("env") or policy.env.value).upper()

    if env == TradeEnv.REAL.value and not policy.real_unlocked:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "REAL trading locked; unlock TradePolicy.real_unlocked after explicit user confirm",
            }
        }

    if any(marker in tool_name for marker in REAL_TOOL_MARKERS):
        if env == TradeEnv.REAL.value and not policy.real_unlocked:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "trade tool blocked in REAL without unlock",
                }
            }

    if tool_input.get("naked_short") and not policy.allow_naked_short:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "naked short disabled by policy",
            }
        }

    return {}
