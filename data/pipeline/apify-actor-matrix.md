# Apify actor matrix — four-site matching

Budget ceiling: **$5.00** (this experiment window).  
Started: 2026-09-02. Ledger: [`apify-smoke-ledger.json`](apify-smoke-ledger.json).

## Candidate shortlist (tried)

| Actor | Role | Result |
|---|---|---|
| `apify/website-content-crawler` + `cheerio` | Static HTML | **Winner for Optionistics** |
| `apify/website-content-crawler` + `playwright:firefox` | JS sites | **Winner for OPC + OptionStrat** |
| `apify/website-content-crawler` + `playwright:adaptive` | Mixed | **Winner for SharePredictions** |
| `apify/cheerio-scraper` | Static alt | Not needed (WCC cheerio already passed) |
| `apify/web-scraper` | Puppeteer | Blocked — needs Apify account permission approve |
| `apify/playwright-scraper` | Playwright custom | Ran but pageFunction returned 0 chars; skipped |
| `apify/puppeteer-scraper` | Last resort | Not needed |

## Winners

| Site | Actor | Config | Smoke run | Stable 2nd page | Batch into `data/raw` | Notes |
|---|---|---|---|---|---|---|
| optionistics | `apify/website-content-crawler` | `crawlerType: cheerio` | `NCYOai3l0Pk3jSb5w` (~$0.0017, 6045 chars) | `53Zk6aaYRb8tKKk50` | `itzKzBM0lWaksMgcS` (4 pages) | Best educational density |
| opc | `apify/website-content-crawler` | `crawlerType: playwright:firefox` | FAQ `kYcYlfgNCUbSml5gc`; long-call `fubGXWqWdHRkOwJd1` | www2 diagonal `QTfPtb6GCrJGg33Ap` | FAQ `xdu5fXpb4WAy08NJ0`; long-call/www2 salvaged from smoke | Plain `www…/diagonal-spread.html` is a shell; many `/calculator/*` pages flake below 1200 chars |
| optionstrat | `apify/website-content-crawler` | `crawlerType: playwright:firefox` | `ZNbfM1By9eDBXrQrO` (2197 chars) | strap `Ol0pHngjT5iY2HyJv` (533 chars, below vault min) | optimizer from smoke; builder `RojKQg6c6fChnXVLV` | Tutorials richer than `/build/*` stubs |
| sharepredictions | `apify/website-content-crawler` | `crawlerType: playwright:adaptive` | `SKLV0DrST6WVaQadR` (4855 chars) | repeat `gLmSvqLsAdHjoMWul` | `cID3Ylt992qsANWc9` | FAQ/product copy only; weak for strategy cards |

## Budget ledger (summary)

See JSON ledger for every run. Experiment spent: **~$0.18** of **$5.00**. Remaining unused.

## Fusion notes

- Same Actor for all four sites → keep `probe.py` on `website-content-crawler`; per-source `crawler_type` override.
- OPC host alias: `www` + `www2`.
- SharePredictions: ingest homepage FAQ as source/meta only, not strategy entities.
- Vault samples: `wiki/sources/Source — Optionistics Chapter 5 Spreads.md` (cited on Diagonal Call Spread, structure only) and `wiki/sources/Source — Options Builder Tutorial.md` (tool UI, not P/L).
