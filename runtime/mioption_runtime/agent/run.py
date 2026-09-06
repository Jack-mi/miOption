"""CLI entry: probe OpenD, run demo webhook bot, or start Agent SDK client."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python -m mioption_runtime.agent.run` from runtime/
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mioption_runtime.agent.hooks import pre_tool_use_gate
from mioption_runtime.agent.system import SYSTEM_PROMPT
from mioption_runtime.agent.tools_mcp import try_create_sdk_server
from mioption_runtime.bot.engine import BotEngine, demo_automation
from mioption_runtime.futu.opend import probe_permissions
from mioption_runtime.futu.policy import TradePolicy
from mioption_runtime.ingress.webhooks import WebhookServer


def cmd_probe(_: argparse.Namespace) -> int:
    print(json.dumps(probe_permissions(), indent=2, default=str))
    return 0


def cmd_demo_webhook(args: argparse.Namespace) -> int:
    policy = TradePolicy()
    engine = BotEngine(automations=[demo_automation(args.hook_id)], policy=policy, prefer_mock=True)

    def run_webhook(hook_id: str, payload: dict) -> dict:
        ctx = {"stock": {"last": float(payload.get("last", 1))}, "indicator": payload}
        return engine.run("webhook", webhook_id=hook_id, context=ctx)

    server = WebhookServer(args.host, args.port, run_webhook)
    server.start_background()
    print(json.dumps({"ok": True, "url": f"http://{args.host}:{server.port}/hooks/{args.hook_id}"}))
    if args.once:
        import urllib.request

        req = urllib.request.Request(
            f"http://127.0.0.1:{server.port}/hooks/{args.hook_id}",
            data=json.dumps({"last": 100}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(resp.read().decode())
        # drive exit monitor with synthetic pnl
        for pos in engine.state.managed.get("positions", {}).values():
            pos["pnl_pct"] = 60.0
        print(json.dumps({"monitor": engine.monitor_tick()}, default=str))
        server.stop()
        return 0
    try:
        import time

        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        server.stop()
    return 0


def cmd_agent(args: argparse.Namespace) -> int:
    policy = TradePolicy()
    if args.unlock_real:
        policy.real_unlocked = True
        from mioption_runtime.futu.policy import TradeEnv

        policy.env = TradeEnv.REAL
    server, tools = try_create_sdk_server(policy=policy)
    if server is None:
        tool_names = []
        for t in tools:
            meta = getattr(t, "_mioption_tool", None)
            if isinstance(meta, dict):
                tool_names.append(str(meta.get("name") or getattr(t, "__name__", "?")))
            else:
                tool_names.append(str(getattr(t, "__name__", "?")))
        print(
            json.dumps(
                {
                    "ok": False,
                    "message": "claude-agent-sdk not installed; tools defined locally only. pip install claude-agent-sdk",
                    "tools": tool_names,
                },
                indent=2,
            )
        )
        return 1
    try:
        import anyio
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, HookMatcher
    except ImportError as exc:
        print(json.dumps({"ok": False, "message": str(exc)}))
        return 1

    async def _gate(input_data, tool_use_id, context):
        return pre_tool_use_gate(input_data, tool_use_id, context, policy=policy)

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"mioption": server},
        allowed_tools=[
            "mcp__mioption__wiki_query",
            "mcp__mioption__futu_probe",
            "mcp__mioption__futu_quote_chain",
            "mcp__mioption__futu_place_option_order",
            "mcp__mioption__bot_run_automation",
        ],
        hooks={"PreToolUse": [HookMatcher(hooks=[_gate])]},
        cwd=str(ROOT.parent),
    )

    async def main() -> None:
        async with ClaudeSDKClient(options=options) as client:
            await client.query(args.prompt)
            async for message in client.receive_response():
                print(message)

    anyio.run(main)
    return 0


def cmd_agent_codex(args: argparse.Namespace) -> int:
    from mioption_runtime.agent.codex_overlay import run_codex_thread, setup_payload

    if args.run:
        payload = run_codex_thread(args.prompt)
    else:
        payload = setup_payload()
        payload["ok"] = True
        payload["message"] = (
            "Codex overlay is optional. Default harness is `agent` (Claude Agent SDK). "
            "Pass --run after `pip install openai-codex` to start a thread."
        )
    print(json.dumps(payload, indent=2, default=str))
    if args.run and not payload.get("ok"):
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="miOption runtime CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("probe", help="Phase A: OpenD / permission probe")
    sp.set_defaults(func=cmd_probe)

    sw = sub.add_parser("demo-webhook", help="Phase C: local webhook bot (mock trade)")
    sw.add_argument("--host", default="127.0.0.1")
    sw.add_argument("--port", type=int, default=0)
    sw.add_argument("--hook-id", default="demo-hook")
    sw.add_argument("--once", action="store_true", help="POST once then run monitor tick")
    sw.set_defaults(func=cmd_demo_webhook)

    sa = sub.add_parser("agent", help="Phase D: default Claude Agent SDK overlay")
    sa.add_argument("--prompt", default="Probe Futu OpenD and summarize connectivity.")
    sa.add_argument("--unlock-real", action="store_true", help="Dangerous: unlock REAL env")
    sa.set_defaults(func=cmd_agent)

    sc = sub.add_parser(
        "agent-codex",
        help="Optional Codex overlay (stdio MCP). Does not replace default agent.",
    )
    sc.add_argument("--prompt", default="Call futu_probe via the mioption MCP and summarize.")
    sc.add_argument(
        "--run",
        action="store_true",
        help="If openai-codex is installed, start a read_only thread; otherwise print setup JSON",
    )
    sc.set_defaults(func=cmd_agent_codex)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
