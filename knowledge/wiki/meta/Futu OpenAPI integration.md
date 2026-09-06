---
type: meta
title: Futu OpenAPI integration
status: evergreen
created: 2026-09-03
updated: 2026-09-04
tags:
  - meta
  - product-spec
  - broker
---

# Futu OpenAPI integration

**Broker and quote bridge for the agent / bot runtime — not a strategy card and not education evidence.**

Do not use this note to fill maximum profit, maximum loss, or break-even on named strategies. Those stay with Options Industry Council text (see [[Futu strategy coverage]]). Bot structure lives in [[Product patterns]]. Education crawl rules stay in [[Source roles]].

Code lives under `runtime/` in the miOption repo, isolated from Apify crawl scripts.

## Role split

| Piece | Role |
|---|---|
| **OpenD** | Local gateway process. User logs into Futu here. Listens on TCP (default `127.0.0.1:11111`). |
| **futu-api** | Official Python SDK. Our process talks to OpenD, not to a public REST “trade URL”. |
| **mioption_runtime.futu** | Thin wrappers: connect, quote, trade, policy. Default trade env is **SIMULATE**. |
| **Agent overlay (default Claude)** | Optional orchestration. Default CLI is `runtime` `agent` (Claude Agent SDK in-process tools + PreToolUse). Codex is an optional overlay via stdio MCP (`agent-codex`); do not switch the default harness. Hooks/sandbox cannot bypass [[Product patterns]] Global Controls in `futu/policy.py`. |

Official AI onboarding (Markdown docs + OpenD skills): [接入 AI 与 OpenClaw](https://openapi.futunn.com/futu-api-doc/intro/ai.html).

## Topology

```text
Agent / Bot / CLI
        │
        ▼
 runtime/mioption_runtime/futu  (policy + SIMULATE default)
        │  TCP localhost
        ▼
     OpenD  (logged-in Futu account)
        │
        ▼
  SIMULATE account  →  later REAL with explicit confirm
```

OpenD is not a cloud substitute. If the listen address is not local, trading requires RSA; development should stay on localhost.

## Environment and safety defaults

| Rule | Default |
|---|---|
| Trade environment | `SIMULATE` |
| REAL / 实盘 | Only when caller sets env explicitly **and** `TradePolicy` allows. Claude PreToolUse is extra; Codex Sandbox is filesystem-only and does not replace trade policy. |
| Unlock trade password | Required by Futu for trading APIs; never log the password |
| Rate limits | Respect OpenD limits (e.g. order burst caps); wrap in `policy.py` |
| Subscriptions | Quote subscriptions consume quota; release unused ones |
| Audit | Log who/when/tool/order id; never invent fill prices in the agent |

If OpenD is down or `futu-api` is missing, tools return a structured connection error. Tests and dry-runs may use the in-process **mock backend**.

## Permissions to probe in Phase A

Before designing live option bots, probe the logged-in OpenD session for:

- US options trading / quote entitlement
- HK options (separate; may need another market vendor story for chain data)
- Account funds and positions on **SIMULATE**
- Market open/closed state for the underlyings we care about

Do not assume App menu coverage ([[Futu strategy coverage]]) equals API entitlement.

## Mapping to 27 strategy entities

[[Futu strategy coverage]] names structures. The runtime order layer should accept a **structure id** plus legs:

- `underlying`, `legs[]` with `{call|put, buy|sell, strike, expiry, qty}`
- optional `exit_rules` attached at open
- payoff display still comes from education text or a future local pricing module — **not** invented by the LLM

Phase B order of work: single-leg simulate → multi-leg vertical / iron structures that match the coverage set.

## Docs for agents

- Prefer the official Markdown download from the Futu OpenAPI site into `docs/futu-api/` (see `runtime/scripts/fetch_futu_docs.sh`). Large dumps may be gitignored; the script re-fetches.
- Optional: install OpenD skills (`install-futu-opend`, `futuapi`) into the coding agent’s skills directory for interactive setup — that assists developers; it is not our production bot.

## What this module is not

- Not an Apify crawl target
- Not a replacement for the knowledge vault Q&A path
- Not Option Alpha, OptionStrat, or any third-party autotrade SaaS API
- Not a place to invent Greeks or max profit numbers

## Related

- [[Product patterns]] — Trigger / Condition / Action, exit rules, global controls
- [[Futu strategy coverage]] — which named structures we cover in the wiki
- [[Source roles]] — education ≠ market data
- [[Product capability map]] — builder/bot layer status
