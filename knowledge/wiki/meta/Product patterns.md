---
type: meta
title: Product patterns
status: evergreen
created: 2026-09-03
updated: 2026-09-06
tags:
  - meta
  - product-spec
---

# Product patterns

**Design spec for a future strategy builder and bot — not a strategy card.**

Do not use this note to answer “what is an iron condor” or to fill maximum profit, maximum loss, or break-even on named entities. Those fields stay with Options Industry Council text (see [[Futu strategy coverage]]). Wiki Q&A should read `wiki/strategies/` and `wiki/concepts/` first; skip this page unless the question is about product UI or bot structure.

None of the sites below is a market-data source. Implement payoff math locally. Broker execution uses **our** broker connection (see [[Futu OpenAPI integration]]), not Option Alpha’s platform and not OSM.AI.

Do not integrate Option Alpha or osmtrade.com as an API. Course landing pages stay catalog-only. Patterns below are **learned shapes** for our own runtime under `runtime/`.

## OptionStrat — strategy builder and payoff view

Evidence: [[Source — Options Builder Tutorial]] (product user interface, not textbook profit and loss).

A builder should let a user pick a named structure, an underlying, expiration, and strikes, then show:

- Net debit or net credit
- Maximum profit and maximum loss **at expiration** (and that assignment or dividend risk is out of scope of that snapshot)
- Break-even underlying price or prices at expiration
- Combined price-sensitivity measures for the whole position
- Estimated profit or loss across a grid of underlying prices (rows) and dates (columns)
- A chart of profit or loss versus underlying price for one selected date, with break-even marked
- A control to shock implied volatility while holding other inputs fixed
- Per-leg include/exclude, quantity, and a custom fill price so an existing broker trade can be reconstructed

Payoff numbers on screen must come from our chain and pricing, never from OptionStrat. `/build/*` page stubs are not knowledge sources.

## Bot automation model (learned shape, our terms)

No long Option Alpha bot-docs page is captured in this vault yet. [Bots 101](https://optionalpha.com/bots-101) and the public [Webhooks](https://optionalpha.com/blog/webhooks) article are locators / marketing outline only, not ingested evidence. Treat the following as a **product outline** for our runtime, not as cited textbook claims.

### Trigger → Condition → Action

| Our term | Meaning | Runtime home |
|---|---|---|
| **Trigger** | When a run starts | `runtime/mioption_runtime/bot/triggers.py`, `ingress/webhooks.py` |
| **Condition** | Filters that must hold (binary Yes/No) | `runtime/mioption_runtime/bot/conditions.py` |
| **Action** | What we send to our broker tools | `runtime/mioption_runtime/bot/actions.py` → Futu trade layer |

**Trigger kinds we implement**

- `schedule` — clock / market-session schedule
- `webhook` — HTTP call to our own `POST /hooks/{id}` (not Option Alpha’s URL)
- `resultant` — fire after our open/close events
- `agent` — default Claude Agent SDK session asks the bot engine to run; optional Codex overlay uses the same bot engine via stdio MCP (`agent-codex`), not as the default harness
- `button` — explicit manual fire (dashboard or CLI)

**Condition families (decision recipes)**

- `stock` — underlying price / move
- `opportunity` — structure filters (DTE band, delta band, credit/debit bounds) once chain exists
- `indicator` — external or computed signals (webhook payload may supply them)
- `position` — open count, P/L %, DTE of held book

Conditions form a small binary tree (Yes/No). First-phase runtime may evaluate a flat AND list; trees can deepen later.

**Actions**

- `open_position` — multi-leg or single-leg order via Futu (default **SIMULATE**)
- `close_position` — flatten or reduce
- `update_exit_rules` — change monitor thresholds without resting exchange stops
- `tag` — label a run or position for later filters

### Scanner vs Monitor

| Role | Intent | Global limits |
|---|---|---|
| **Scanner** | Search and **open** | Must respect allocation and position caps; skip opens when capped |
| **Monitor** | Manage and **close** | May close freely; opening from a monitor still hits the same hard caps |

Same engine; the labels are convenience and default policy, not separate languages.

### Global Controls (hard gates before any open)

Checked **before** an open action leaves the policy layer:

1. **Allocation** — capital the bot may use
2. **Daily position limit** — opens allowed today
3. **Max position limit** — concurrent opens

Violation → **no order**, structured error only. Agent hooks and `policy.py` both enforce this; the agent must not bypass policy.

### Exit rules (our name for “Exit Options”)

Learned behavior to copy into our monitor loop:

- Evaluate held positions on a timer (default once per minute in session; optional faster path later)
- Criteria examples: profit-take %, stop-loss %, max DTE remaining, avoid-event dates
- **Do not** park resting stop orders at the exchange by default; when criteria hit, **then** send a close
- Attach default exit rules at open; automations may **update_exit_rules** while the position is live

Implementation: `runtime/mioption_runtime/bot/exit_monitor.py`.

### External signal ingress (webhook pattern)

Learned from the public Webhooks article shape:

1. We mint a secret hook id and URL on **our** ingress
2. An automation binds `trigger: webhook` to that id
3. TradingView / Zapier / Python / Agent POSTs to us
4. We run Conditions → Actions on our broker

A hook may fan out to a bounded number of automations. We never call Option Alpha’s webhook API as a data feed (see [[Source roles]]).

### Mapping table (Option Alpha vocabulary → ours)

| Learned vocabulary | Our side |
|---|---|
| Webhook trigger | `ingress/webhooks.py` + `trigger: webhook` |
| Decision recipes | `conditions.py` / Agent `check_*` tools |
| Open / Close Position | Futu order tools (default SIMULATE) |
| Exit Options | Exit rules + `exit_monitor.py` |
| Global Controls | `futu/policy.py` + Agent `PreToolUse` hooks |
| SmartPricing | Later: our quote/revise loop on Futu multi-leg orders |

## Optionistics — screener dimensions to copy, not to scrape

Learning Center lessons are education (secondary). The public screener is a **filter list to imitate**, not a crawl target. Candidate dimensions:

- High or low implied volatility versus a straddle or similar structure
- Unusual volume

Compute those filters in a later market-data module. Do not ingest delayed quote tables from optionistics.com.

## OSM.AI — seller-desk lifecycle (learned shape, not an API)

Public product pages describe a research desk for **defined-risk credit verticals**: scan a universe, emit a two-leg seller card, then follow with protection / take-profit / settlement records. That lifecycle is the shape we copy into `runtime/mioption_runtime/seller/`.

| Learned OSM idea | Our side |
|---|---|
| Discover / Structure cards | `seller/scan.py` on OpenD; structures `bull_put_spread` and `bear_call_spread` only |
| Adopt / watch / reject | `seller_verdict` — records a judgment, does not place an order |
| Protection / take-profit windows | `seller/monitor.py` — mid-mark alerts; default is remind-only |
| Decision archive | `runtime/data/seller/` JSON (gitignored); research basis = mids, no fees |
| Local follow script | `runtime/scripts/seller_follow.py` against **our** cards; default dry-run |

Do not call osmtrade APIs, scrape live OSM cards, or copy their opportunity score / IV Rank. Payoff on a card is OIC width-minus-credit math plus OpenD bids and asks. Futu SIMULATE does not support combo option orders; follow either research-marks only or optional sequential legs with an explicit warning.

Forced protection and rolls stay `planned` until we ship them.

## Related

- [[Futu OpenAPI integration]] — OpenD, SIMULATE default, permissions, rate limits
- [[Source roles]] — education evidence vs forbidden market-data uses
- [[Futu strategy coverage]] — 27 named structures for legs / naming only
- [[Product capability map]] — knowledge Q&A / market data / builder+bot layers
