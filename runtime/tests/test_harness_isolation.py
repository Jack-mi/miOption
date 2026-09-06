from __future__ import annotations

import ast
from pathlib import Path

from mioption_runtime.agent.tool_handlers import TOOL_DEFS, ToolRuntime

RUNTIME = Path(__file__).resolve().parents[1] / "mioption_runtime"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_futu_and_bot_are_sdk_agnostic():
    banned = {"claude_agent_sdk", "openai_codex", "fastmcp"}
    for folder in ("futu", "bot", "ingress", "seller"):
        for py in (RUNTIME / folder).glob("*.py"):
            assert banned.isdisjoint(_imports(py)), py


def test_dispatch_probe_and_mock_order():
    rt = ToolRuntime()
    probe = rt.dispatch("futu_probe", {})
    assert "tcp_open" in probe
    chain = rt.dispatch("futu_quote_chain", {"underlying": "US.SPY"})
    assert chain["contracts"]
    first = chain["contracts"][0]
    placed = rt.dispatch(
        "futu_place_option_order",
        {"underlying": "US.SPY", "code": first["code"], "side": "BUY", "qty": 1, "price": 1.0},
    )
    assert placed["ok"] is True
    assert placed["env"] == "SIMULATE"


def test_wiki_query_finds_iron_condor():
    rt = ToolRuntime()
    result = rt.dispatch("wiki_query", {"query": "iron condor", "top": 5})
    assert result["candidates"]
    paths = " ".join(str(c.get("page_path") or "") for c in result["candidates"]).lower()
    assert "condor" in paths or "iron" in paths


def test_seller_list_cards_dispatch():
    rt = ToolRuntime()
    listed = rt.dispatch("seller_list_cards", {})
    assert "cards" in listed
    assert "count" in listed


def test_tool_defs_include_wiki_query():
    assert {d["name"] for d in TOOL_DEFS} >= {
        "wiki_query",
        "futu_probe",
        "futu_quote_chain",
        "futu_place_option_order",
        "bot_run_automation",
        "seller_scan",
        "seller_list_cards",
        "seller_verdict",
        "seller_monitor_tick",
    }
