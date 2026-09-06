---
type: meta
title: Source roles
status: evergreen
created: 2026-09-03
updated: 2026-09-06
tags:
  - meta
  - source-policy
---

# Source roles

This vault stores **education evidence**. A site on the crawl allowlist is not automatically a market-data feed or a product to copy numbers from.

For strategy questions (what a position is, legs, published maximum profit or loss), start at [[Futu strategy coverage]] and the named strategy notes. Do not treat [[Product patterns]] as textbook evidence.

## Education evidence

Use these pages to fill concepts and the 27 strategy entities.

| Publisher | Role in this vault |
|---|---|
| Options Industry Council | Primary text for strategy meaning, legs, and published profit-and-loss language |
| Wikipedia | Point fills only (margin, bid-ask, diagonal, straddle). Not a dump |
| CME Institute | Education. The captured whitepaper is about options on futures exercise, not live prices |
| Cboe Options Institute | Education if a page has independent text. Course catalogs are not eligible |
| Optionistics Learning Center | Secondary structure and naming. Profit-and-loss numbers stay with the Options Industry Council |

## Product patterns (not data)

[[Product patterns]] records how OptionStrat, Option Alpha, Optionistics screeners, and OSM.AI **look and behave**. Those sites have no public market-data API for this project. Do not copy calculator outputs onto strategy cards. Do not crawl `/build` stubs or screener quote tables.

OSM.AI / osmtrade.com is a **learned seller-desk shape** only. Do not call its API, download `osm_follow.py`, ingest its signal cards, or treat its mid-mark ledger as education evidence. Our scanner uses OpenD; payoff language stays with the Options Industry Council.

## Not crawled as market data

These belong in a later data module, not in Apify page capture:

- CME Market Data (REST / WebSocket / reference data)
- Cboe DataShop / LiveVol
- Delayed or live option chains from Yahoo, Polygon, Tradier, or similar
- OptionStrat flow, Option Alpha webhooks-as-data, Optionistics delayed quotes
- OSM.AI / osmtrade.com cards, follow scripts, or research API

CME Institute pages are not the CME Market Data API. Cboe Options Institute pages are not Cboe DataShop.

See the product-capability board at `wiki/canvases/product-stack.canvas`.
