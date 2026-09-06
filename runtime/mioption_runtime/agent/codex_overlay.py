"""Optional Codex SDK overlay. Default harness remains Claude Agent SDK."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .system import SYSTEM_PROMPT
from .tool_handlers import TOOL_DEFS

RUNTIME_ROOT = Path(__file__).resolve().parents[2]


def mcp_stdio_command() -> dict[str, object]:
    return {
        "command": sys.executable,
        "args": ["-m", "mioption_runtime.agent.stdio_mcp"],
        "cwd": str(RUNTIME_ROOT),
    }


def setup_payload() -> dict[str, object]:
    return {
        "ok": False,
        "default_harness": "claude-agent-sdk",
        "message": (
            "Codex is an optional overlay. Install openai-codex, login (ChatGPT or API key), "
            "point Codex MCP at python -m mioption_runtime.agent.stdio_mcp. "
            "Do not switch the default `agent` command."
        ),
        "stdio_mcp": mcp_stdio_command(),
        "config_toml": (
            "[mcp_servers.mioption]\n"
            f'command = "{sys.executable}"\n'
            'args = ["-m", "mioption_runtime.agent.stdio_mcp"]\n'
            "startup_timeout_sec = 15\n"
        ),
        "tools": [d["name"] for d in TOOL_DEFS],
        "sandbox": "read_only",
        "note": "Codex Sandbox is filesystem access, not trade policy. REAL still needs TradePolicy unlock.",
    }


def run_codex_thread(prompt: str) -> dict[str, object]:
    try:
        from openai_codex import Codex, Sandbox
    except ImportError:
        payload = setup_payload()
        payload["error"] = "openai-codex not installed"
        return payload

    mcp = mcp_stdio_command()
    with Codex() as codex:
        thread = codex.thread_start(
            sandbox=Sandbox.read_only,
            developer_instructions=SYSTEM_PROMPT,
            cwd=str(RUNTIME_ROOT.parent),
            config={
                "mcp_servers": {
                    "mioption": {
                        "command": mcp["command"],
                        "args": mcp["args"],
                    }
                }
            },
        )
        result = thread.run(prompt)
        return {
            "ok": True,
            "harness": "openai-codex",
            "thread_id": getattr(thread, "id", None),
            "final_response": getattr(result, "final_response", str(result)),
        }
