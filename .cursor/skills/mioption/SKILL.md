---
name: mioption
description: >-
  Route miOption knowledge questions to the vault and trading actions to
  FastMCP tools. Use when the user asks about option strategies, published
  P/L, OpenD, Futu orders, scanners, bots, or the mioption MCP.
---

# miOption: vault for knowledge, MCP for trading

This repo is both an Obsidian options wiki and a local Futu runtime. Do not
mix the two evidence sources.

## Route

| User intent | Do this | Do not |
|---|---|---|
| What is a strategy, max profit/loss, break-even, Greeks meaning | Call MCP `wiki_query`. Cite returned `page_path`. | Invent numbers. Do not fill P/L from `wiki/meta/Product patterns.md` or `wiki/meta/Futu OpenAPI integration.md`. |
| Probe OpenD, option chain, place/simulate order, run a bot, seller cards | Call MCP trade tools | Use Bash as a second trade channel |
| Option Alpha / OptionStrat / OSM.AI as a live API | Refuse | Treat OA webhooks, OSM cards, or OSM follow scripts as our execution path |

If MCP `wiki_query` is unavailable, fall back to the `wiki-query` skill / claude-obsidian CLI. Prefer MCP when the `mioption` server is connected.

## Trade tools (default SIMULATE)

- `futu_probe` — OpenD up/down and permissions. Unreachable OpenD is a valid result.
- `futu_quote_chain` — chain for an underlying (`US.SPY` style). Mock unless `MIOPTION_FUTU_MOCK=0`.
- `futu_place_option_order` — default `env=SIMULATE`. REAL only if the user explicitly asked and policy unlocks it.
- `bot_run_automation` — Trigger → Condition → Action engine. Not Option Alpha.
- `seller_scan` / `seller_list_cards` / `seller_verdict` / `seller_monitor_tick` — local seller desk (OpenD). Not OSM.AI. Verdicts do not place orders. Same loop is on the vault-map H5 `desk.html` (`python runtime/scripts/serve_h5.py`).

Never invent fill prices. Use tool return values. Naked shorts stay blocked unless policy allows.

## Knowledge rules

- Evidence lives under `knowledge/wiki/strategies/` and `knowledge/wiki/concepts/`.
- `not_payoff_evidence: true` means skip that page for max profit/loss/break-even.
- If candidates are empty, say the vault cannot answer and stop. Do not complete from model memory.

## Hosts

Cursor loads this skill from `.cursor/skills/mioption/` and the FastMCP server from `.cursor/mcp.json`. OpenCode loads `.opencode/skills/mioption/` and repo `opencode.json`. Other hosts copy `embed/hosts/` snippets; they must point at the same `python -m mioption_runtime.agent.stdio_mcp` entry.
