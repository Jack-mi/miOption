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
- [[Strap]] / [[Strip]]: Wikipedia Straddle section confirms legs and bullish/bearish tilt. Numeric P/L still not published.
- [[Naked Put (Uncovered Put, Short Put)]]: OIC text page, same fields as Naked Call.

## 2026-09-02 — Four-site Apify matching

Matched `apify/website-content-crawler` per site (cheerio / firefox / adaptive). Stored winner-batch pages in `data/raw/pages`. Vault fusion samples: [[Source — Optionistics Chapter 5 Spreads]] (cited by [[Diagonal Call Spread]] for structure only) and [[Source — Options Builder Tutorial]] (tool UI; not used as strategy P/L). SharePredictions homepage is raw evidence only.

## 2026-09-02 — New-topic crawl (`new-topics-1usd`)

Apify `website-content-crawler` run `dwOriSJHmglF1wbJA` stored four pages (~`$0.0043`): OIC getting-started (margin), CME options-on-futures whitepaper, Wikipedia margin, Wikipedia bid–ask. Added [[Options margin and account approval]], [[Options on futures exercise and assignment]], [[Bid-ask spread and liquidity cost]].

## 2026-09-03 — Optionistics Learning Center lessons

Cheerio batches `optionistics-lc-1`–`3` stored 19 lessons (≥1200 chars). Added 19 source notes. Fused structure/naming only onto [[Option contract]], [[Equity options basics]], [[Options risk, leverage, and hedging]], [[Option premium and pricing drivers]], [[Vega and implied volatility sensitivity]], [[Covered Call (Buy-Write)]], [[Long Straddle]], and [[Short Straddle]]. Conversions and synthetic positions are source notes only (not Futu coverage-set entities). P/L remains OIC. Short lessons under 1200 chars were skipped, not lowered.

