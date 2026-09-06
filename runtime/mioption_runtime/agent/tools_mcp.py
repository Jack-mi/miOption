"""In-process MCP tools for the default Claude Agent SDK overlay."""

from __future__ import annotations

from typing import Any, Callable

from .tool_handlers import TOOL_DEFS, ToolRuntime, text_result
from ..futu.policy import TradePolicy
from ..bot.engine import BotEngine


def _tool_decorator_fallback(name: str, description: str, schema: dict[str, Any]):
    def deco(fn: Callable):
        fn._mioption_tool = {"name": name, "description": description, "schema": schema}
        return fn

    return deco


try:
    from claude_agent_sdk import tool as sdk_tool
except ImportError:  # pragma: no cover
    sdk_tool = _tool_decorator_fallback  # type: ignore[assignment]


def _py_schema(defn: dict[str, Any]) -> dict[str, Any]:
    props = (defn.get("inputSchema") or {}).get("properties") or {}
    mapping = {"string": str, "number": float, "boolean": bool}
    out: dict[str, Any] = {}
    for key, spec in props.items():
        out[key] = mapping.get(str(spec.get("type")), str)
    return out


def build_tools(policy: TradePolicy | None = None, engine: BotEngine | None = None):
    runtime = ToolRuntime(policy=policy, engine=engine)
    tools = []
    for defn in TOOL_DEFS:
        name = str(defn["name"])

        @sdk_tool(name, str(defn["description"]), _py_schema(defn))
        async def _handler(args: dict[str, Any], *, _name: str = name):
            return text_result(runtime.dispatch(_name, args))

        _handler.__name__ = name
        tools.append(_handler)
    return tools


def try_create_sdk_server(policy: TradePolicy | None = None, engine: BotEngine | None = None):
    """Return (server, tools) when claude-agent-sdk is installed; else (None, tools)."""
    tools = build_tools(policy=policy, engine=engine)
    try:
        from claude_agent_sdk import create_sdk_mcp_server
    except ImportError:
        return None, tools
    server = create_sdk_mcp_server(name="mioption", version="0.1.0", tools=tools)
    return server, tools
