from __future__ import annotations

import pytest

from mioption_runtime.agent.tools_mcp import try_create_sdk_server

pytest.importorskip("claude_agent_sdk")


def test_sdk_mcp_server_is_created():
    server, tools = try_create_sdk_server()
    assert server is not None
    names = {getattr(t, "name", getattr(t, "__name__", "")) for t in tools}
    assert names >= {
        "wiki_query",
        "futu_probe",
        "futu_quote_chain",
        "futu_place_option_order",
        "bot_run_automation",
    }
