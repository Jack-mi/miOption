# miOption runtime

Broker / bot / agent runtime for Futu OpenAPI integration. **Isolated from** the knowledge crawl under `scripts/` and `data/pipeline/`.

Specs:

- `knowledge/wiki/meta/Product patterns.md` — Trigger / Condition / Action, exit rules, global controls
- `knowledge/wiki/meta/Futu OpenAPI integration.md` — OpenD, SIMULATE default, permissions

**Cursor embed path is FastMCP stdio** (`python -m mioption_runtime.agent.stdio_mcp`), wired from repo `.cursor/mcp.json`. Futu (`futu/`) and the bot engine (`bot/`) stay SDK-agnostic: trade policy lives in `futu/policy.py`, not in an LLM overlay. The optional `agent` CLI still uses Claude Agent SDK; Codex is an optional overlay (`agent-codex`). Neither SDK is required for Cursor to call the tools.

## Setup

```bash
cd runtime
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Pin FastMCP exactly (`fastmcp==4.0.3`). Do not launch with `uv run --with fastmcp`; that skips `futu-api`.

Cursor (this repo): `.cursor/mcp.json` starts the venv interpreter with `PYTHONPATH=runtime`, `MIOPTION_FUTU_MOCK=0` (live OpenD), and `MIOPTION_VAULT=knowledge`. Skill: `.cursor/skills/mioption/SKILL.md`. Other hosts: `embed/hosts/` (examples stay mock).

Default trade path uses an in-process **mock** (`MIOPTION_FUTU_MOCK=1`). For live OpenD:

1. Install and login [OpenD](https://openapi.futunn.com/futu-api-doc/quick/opend-base.html)
2. `export MIOPTION_FUTU_MOCK=0`
3. `python scripts/check_opend.py`

## CLI

```bash
# Phase A — connectivity
python -m mioption_runtime.agent.run probe

# Phase C — webhook bot (mock) one-shot open + exit monitor
python -m mioption_runtime.agent.run demo-webhook --once

# Phase D — default harness: Claude Agent SDK
python -m mioption_runtime.agent.run agent --prompt "Call futu_probe and summarize."

# Optional Codex overlay (does not replace `agent`)
python -m mioption_runtime.agent.run agent-codex
# after: pip install openai-codex && ChatGPT/API login
python -m mioption_runtime.agent.run agent-codex --run --prompt "Call futu_probe and summarize."
```

`agent` needs a reachable Anthropic API (or Claude Code login). If the API is refused, MCP tools still register (`futu_probe` etc.). If `claude-agent-sdk` is missing, `agent` prints the local tool list and exits 1; hooks and bot/Futu tools still work under tests and `demo-webhook`.

The FastMCP server is `python -m mioption_runtime.agent.stdio_mcp` (tools: `wiki_query`, `futu_probe`, `futu_quote_chain`, `futu_place_option_order`, `bot_run_automation`, `seller_scan`, `seller_list_cards`, `seller_verdict`, `seller_monitor_tick`). Codex overlay, if used, talks to that same command. Codex `Sandbox` is filesystem access only; REAL orders still require `TradePolicy` unlock. Example wiring: `runtime/.codex/config.toml.example`.

## Seller desk (v1)

Learned OSM-shaped lifecycle, **not** osmtrade.com. Scan OpenD, write two-leg credit cards, mark mids, optional local follow.

```bash
# cards (default SIMULATE quotes unless MIOPTION_FUTU_MOCK=0)
python scripts/seller_desk.py scan --underlyings US.BIDU
python scripts/seller_desk.py list
python scripts/seller_desk.py verdict CARD_ID adopt
python scripts/seller_desk.py monitor

# follow adopted cards; dry-run unless --submit
python scripts/seller_follow.py
python scripts/seller_follow.py --submit --legs sequential
```

JSON archive: `runtime/data/seller/` (gitignored). Touch `runtime/data/seller/STOP` to halt follow. Futu SIMULATE cannot place combo option orders; sequential legs are opt-in and tagged `leg_risk: sequential`.

## Layout

```text
mioption_runtime/
  futu/     OpenD probe, quote, trade, policy (no Claude/Codex imports)
  bot/      Trigger → Condition → Action + exit monitor (no Claude/Codex imports)
  seller/   Credit-vertical cards, scan, monitor, follow (no OSM)
  ingress/  POST /hooks/{id}
  agent/    FastMCP stdio server; optional Claude/Codex CLI overlays
```

## Safety

- Default env: **SIMULATE**
- REAL requires `TradePolicy.real_unlocked` and agent hook approval
- Naked shorts disabled by default
- Do not invent fill prices or payoff numbers in the agent layer
