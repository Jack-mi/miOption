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

JSON archives and quote databases are separated under `runtime/data/mock/` and `runtime/data/live/` (gitignored). The mode is selected by `MIOPTION_FUTU_MOCK`, default `1`; the workbench sets it from `--mode`. `MIOPTION_SELLER_DIR` and `MIOPTION_QUOTES_DB` override explicit locations. Old `runtime/data/seller/` and `runtime/data/quotes.sqlite` remain untouched and are not silently imported. Touch `STOP` inside the active seller directory to halt follow. Futu SIMULATE cannot place combo option orders; sequential legs remain a separate opt-in CLI path, not part of browser acceptance.

H5 workbench (scan / list / verdict / monitor, **never places orders**):

```bash
python scripts/serve_h5.py --mode mock --chat
# open http://127.0.0.1:8765/chain.html, desk.html, or chat.html
```

Use `--mode live` after logging into OpenD for real market data. The default H5 port is `8765`; the managed OpenCode chat port is `4097` (`--port` / `--chat-port` override them). The launcher never kills an existing listener. Ctrl-C or SIGTERM stops only the child chat it created. `--chat` uses the installed `opencode serve --pure`, skips external plugins, and defaults to `opencode-go/deepseek-v4-flash`; use `--model` for another authenticated provider/model. The workspace, backend address and model reach the frontend through `/api/config`, not hardcoded personal paths.

H5 and its chat MCP share the same mode and data paths, including the `futu_quote_chain` cache. The child chat disables external Claude/agent skills without changing global configuration, so unrelated malformed skills do not break the workbench. `MIOPTION_RESEARCH_ONLY=1` removes the order and bot-automation MCP tools and independently rejects their dispatch. Browser writes are same-origin and the server only accepts loopback Host values.

Research workflow: pull one symbol on `chain.html` → scan it on `desk.html` → inspect the source note → adopt/watch/reject → monitor. Quotes older than 72 hours (or with missing timestamps) cannot be scanned or marked until refreshed; this is a local snapshot-age guard, not an exchange-session or latency guarantee. Mock data never marks a live card. Rescanning preserves adopted cards and their original credit basis. Expired cards emit `expiry_review`; the system does not invent a realized settlement P/L from the current spot price.

For dry-run follow of the live-data archive, from `runtime/`:

```bash
MIOPTION_FUTU_MOCK=0 .venv/bin/python scripts/seller_follow.py --whitelist US.BIDU
```

No `--submit` is needed for research. Monitor is on-demand; an unattended scheduler and broker settlement reconciliation are not enabled.

## Verify

From the repository root:

```bash
scratch=$(mktemp -d)
PYTHONPATH=runtime MIOPTION_FUTU_MOCK=1 MIOPTION_SELLER_DIR="$scratch/seller" MIOPTION_QUOTES_DB="$scratch/quotes.sqlite" runtime/.venv/bin/python -m pytest runtime/tests -q
python3 scripts/probe.py --check
python3 scripts/build_knowledge.py --check
python3 vendor/claude-obsidian/scripts/claude-obsidian.py doctor --vault knowledge
python3 vendor/claude-obsidian/scripts/claude-obsidian.py lint --vault knowledge --as-of 2026-09-20
```

The archive builder intentionally reads its frozen 39-document index, not the live 72-document crawl index. It validates 22 historical strategies; the active vault contains 27. See `docs/end-to-end.md` for the browser/live acceptance checklist.

## Layout

```text
mioption_runtime/
  futu/     OpenD probe, quote, trade, policy (no Claude/Codex imports)
  bot/      Trigger → Condition → Action + exit monitor (no Claude/Codex imports)
  seller/   Credit-vertical cards, scan, monitor, follow (no OSM)
  ingress/  POST /hooks/{id}; vault-map H5 + /api/seller/*
  agent/    FastMCP stdio server; optional Claude/Codex CLI overlays
```

## Safety

- Default env: **SIMULATE**
- REAL requires `TradePolicy.real_unlocked` and agent hook approval
- Naked shorts disabled by default
- Do not invent fill prices or payoff numbers in the agent layer
