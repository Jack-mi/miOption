from __future__ import annotations

from pathlib import Path

import pytest

from mioption_runtime.agent.stdio_mcp import build_mcp
from mioption_runtime.agent.tool_handlers import TOOL_DEFS, ToolRuntime

pytest.importorskip("fastmcp")


def _result_payload(result) -> str:
    data = getattr(result, "data", None)
    if data is not None:
        return str(data)
    content = getattr(result, "content", None) or []
    if content:
        return str(getattr(content[0], "text", content[0]))
    return str(result)


@pytest.fixture
async def client():
    from fastmcp import Client

    async with Client(build_mcp(ToolRuntime())) as mcp_client:
        yield mcp_client


async def test_fastmcp_lists_expected_tools(client):
    tools = await client.list_tools()
    names = {t.name for t in tools}
    assert names == {d["name"] for d in TOOL_DEFS}


async def test_fastmcp_probe_and_mock_chain(client):
    probe = await client.call_tool("futu_probe", {})
    assert "tcp_open" in _result_payload(probe)
    chain = await client.call_tool("futu_quote_chain", {"underlying": "US.SPY"})
    payload = chain.data if getattr(chain, "data", None) is not None else None
    assert payload is not None
    assert payload["contracts"]
    first = payload["contracts"][0]
    placed = await client.call_tool(
        "futu_place_option_order",
        {
            "underlying": "US.SPY",
            "code": first["code"],
            "side": "BUY",
            "qty": 1,
            "price": 1.0,
        },
    )
    order = placed.data
    assert order["ok"] is True
    assert order["env"] == "SIMULATE"


async def test_fastmcp_wiki_query(client):
    result = await client.call_tool("wiki_query", {"query": "iron condor", "top": 5})
    payload = result.data
    assert payload["candidates"]
    paths = " ".join(str(c.get("page_path") or "") for c in payload["candidates"]).lower()
    assert "condor" in paths or "iron" in paths


async def test_stdio_command_matches_cursor_mcp_json():
    from fastmcp import Client
    from fastmcp.client.transports.stdio import StdioTransport

    repo = Path(__file__).resolve().parents[2]
    python = repo / "runtime" / ".venv" / "bin" / "python"
    if not python.is_file():
        pytest.skip("runtime/.venv missing")
    transport = StdioTransport(
        command=str(python),
        args=["-m", "mioption_runtime.agent.stdio_mcp"],
        env={
            "PYTHONPATH": str(repo / "runtime"),
            "MIOPTION_FUTU_MOCK": "1",
            "MIOPTION_VAULT": str(repo / "knowledge"),
        },
        cwd=str(repo / "runtime"),
    )
    async with Client(transport) as stdio_client:
        tools = await stdio_client.list_tools()
        names = {t.name for t in tools}
        assert names == {d["name"] for d in TOOL_DEFS}
        wiki = await stdio_client.call_tool("wiki_query", {"query": "iron condor", "top": 3})
        paths = " ".join(str(c.get("page_path") or "") for c in wiki.data["candidates"]).lower()
        assert "condor" in paths
        probe = await stdio_client.call_tool("futu_probe", {})
        assert "tcp_open" in probe.data
