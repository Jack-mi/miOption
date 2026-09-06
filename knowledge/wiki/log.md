---
type: meta
title: Wiki Log
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - meta
  - log
---

# Wiki Log

## 2026-09-04 — Agent harness stays Claude; Codex optional

Recorded that `runtime/` keeps Claude Agent SDK as the default overlay. Futu and bot modules stay SDK-agnostic. Codex may attach later through stdio MCP (`python -m mioption_runtime.agent.stdio_mcp`) via `agent-codex`; Codex filesystem sandbox is not trade policy. See [[Futu OpenAPI integration]] and [[Product patterns]].

## 2026-09-03 — Bot patterns and Futu OpenAPI bridge

Expanded [[Product patterns]] with our Trigger / Condition / Action model, Scanner vs Monitor, Global Controls, exit rules, and self-hosted webhook ingress (learned shapes; not an Option Alpha API). Added [[Futu OpenAPI integration]] for OpenD + futu-api, SIMULATE default, and runtime module boundaries under `runtime/`. Strategy entity count is still 27.

## 2026-09-02 — Import archived JSON knowledge

Migrated the JSON knowledge layer into this vault:

- 39 source notes from admitted crawl pages
- 10 concept notes from published items
- 22 strategy entities from strategy cards
- 5 relations rewritten as wikilinks

`strategy.diagonal_spread` remains developing until dedicated diagonal evidence exists.

## 2026-09-02 — Merge Futu menu with topic474

Merged App strategy menu and [常用期权组合简介](https://support.futunn.com/topic474) into one coverage set.

- Added [[Long Put Butterfly]] and [[Long Put Calendar Spread]] from OIC text pages
- Added [[Strap]] and [[Strip]] as developing (Futu structure only; no OIC pages)
- Positioning source: [[Source — Futu 常用期权组合简介]]

## 2026-09-02 — Wikipedia handling for diagonal / strap / strip; Naked Put

- [[Diagonal Call Spread]]: Wikipedia dedicated page. Structure published; no single max-gain/max-loss/breakeven. Calendar numbers removed.
- [[Strap]] / [[Strip]]: Wikipedia Straddle section confirms legs and bullish/bearish tilt. Numeric profit and loss is still not published.
- [[Naked Put (Uncovered Put, Short Put)]]: OIC text page, same fields as Naked Call.

## 2026-09-02 — Four-site Apify matching

Matched `apify/website-content-crawler` per site (cheerio / firefox / adaptive). Stored winner-batch pages in `data/raw/pages`. Vault fusion samples: [[Source — Optionistics Chapter 5 Spreads]] (cited by [[Diagonal Call Spread]] for structure only) and [[Source — Options Builder Tutorial]] (tool user interface; not used as strategy-card profit and loss). SharePredictions homepage is raw evidence only.

## 2026-09-02 — New-topic crawl (`new-topics-1usd`)

Apify `website-content-crawler` run `dwOriSJHmglF1wbJA` stored four pages (~`$0.0043`): OIC getting-started (margin), CME options-on-futures whitepaper, Wikipedia margin, Wikipedia bid–ask. Added [[Options margin and account approval]], [[Options on futures exercise and assignment]], [[Bid-ask spread and liquidity cost]].

## 2026-09-03 — Optionistics Learning Center lessons

Cheerio batches `optionistics-lc-1`–`3` stored 19 lessons (≥1200 chars). Added 19 source notes. Fused structure/naming only onto [[Option contract]], [[Equity options basics]], [[Options risk, leverage, and hedging]], [[Option premium and pricing drivers]], [[Vega and implied volatility sensitivity]], [[Covered Call (Buy-Write)]], [[Long Straddle]], and [[Short Straddle]]. Conversions and synthetic positions are source notes only (not Futu coverage-set entities). Profit-and-loss numbers remain those published by the Options Industry Council. Short lessons under 1200 chars were skipped, not lowered.

## 2026-09-03 — Plain-language pass

Expanded shorthand in wiki running text (for example profit and loss instead of P/L, at-the-money instead of ATM). Source quotations and published payoff numbers were left unchanged. Strategy coverage is still 27 entities.

## 2026-09-03 — Source roles and product patterns

Recorded how crawl sources are used: education text versus sites that must not be treated as live market data. Added [[Source roles]] and [[Product patterns]] (OptionStrat builder fields from [[Source — Options Builder Tutorial]]; Option Alpha trigger/condition/action as an uncaptured outline). Strategy entity count is still 27. Q&A should not treat product-pattern notes as textbook profit-and-loss.

## 2026-09-03 — Product capability canvas

Added [[Product capability map]] (`wiki/canvases/product-stack.canvas`): knowledge Q&A (landed), market data (not built), builder and bot (not built). This is not the education-versus-price-feed table on [[Source roles]].

