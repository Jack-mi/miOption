from mioption_runtime.agent.hooks import pre_tool_use_gate
from mioption_runtime.futu.policy import TradeEnv, TradePolicy


def test_deny_real_when_locked():
    policy = TradePolicy(env=TradeEnv.SIMULATE, real_unlocked=False)
    out = pre_tool_use_gate(
        {
            "tool_name": "mcp__mioption__futu_place_option_order",
            "tool_input": {"env": "REAL"},
        },
        None,
        None,
        policy=policy,
    )
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_deny_non_us_before_data_agent():
    policy = TradePolicy()
    out = pre_tool_use_gate(
        {"tool_name": "mcp__mioption__data_agent", "tool_input": {"ticker": "HK.00700"}},
        None,
        None,
        policy=policy,
    )
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert out["hookSpecificOutput"]["permissionDecisionReason"] == "只覆盖美股"


def test_allow_simulate():
    policy = TradePolicy()
    out = pre_tool_use_gate(
        {
            "tool_name": "mcp__mioption__futu_place_option_order",
            "tool_input": {"env": "SIMULATE"},
        },
        None,
        None,
        policy=policy,
    )
    assert out == {}
