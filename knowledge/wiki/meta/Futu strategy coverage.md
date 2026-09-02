---
type: meta
title: Futu strategy coverage
status: evergreen
created: 2026-09-02
updated: 2026-09-02
tags:
  - meta
  - coverage
---

# Futu strategy coverage

One merged set from two Futu surfaces:

- App strategy menu (product categories: single-leg, covered, collar, diagonal, iron butterfly, and the rest of the named menu)
- Help article [常用期权组合简介](https://support.futunn.com/topic474) (combo structures #1–12)

Evidence for P/L and Greeks is OIC text, except Strap/Strip (Wikipedia + Futu structure; no numeric P/L) and Diagonal (Wikipedia: analyze each variation individually).

Positioning source: [[Source — Futu 常用期权组合简介]]

## 单腿期权 / Single Option

Category status: `ready`. App menu; not in topic474.

- [[Long Call]] — `ready`
- [[Long Put]] — `ready`
- [[Naked Call (Uncovered Call, Short Call)]] — `ready`
- [[Naked Put (Uncovered Put, Short Put)]] — `ready`
- [[Protective Put (Married Put)]] — `ready`

## 垂直策略 / Vertical Spread

Category status: `ready`. topic474 #1–4.

- [[Bull Call Spread (Debit Call Spread)]] — `ready` — Bull call spread
- [[Bull Put Spread (Credit Put Spread)]] — `ready` — Bull put spread
- [[Bear Call Spread (Credit Call Spread)]] — `ready` — Bear call spread
- [[Bear Put Spread]] — `ready` — Bear put spread

## 股票担保 / Covered Stock

Category status: `ready`. App menu; not in topic474.

- [[Covered Call (Buy-Write)]] — `ready`
- [[Cash-Secured Put]] — `ready`

## 领口策略 / Collar

Category status: `ready`. App menu; not in topic474.

- [[Collar (Protective Collar)]] — `ready`

## 跨式策略 / Straddle

Category status: `ready`. topic474 #10 (buy or sell).

- [[Long Straddle]] — `ready`
- [[Short Straddle]] — `ready`

## 宽跨式策略 / Strangle

Category status: `ready`. topic474 #11 (buy or sell).

- [[Long Strangle (Long Combination)]] — `ready`
- [[Short Strangle]] — `ready`

## 带式 / 条式 / Strap and Strip

Category status: `ready` for structure. topic474 #8–9 plus Wikipedia Straddle. Numeric max gain / max loss / breakeven are not published on those sources.

- [[Strap]] — `ready` — 买 2 call + 买 1 put；偏多的跨式变体
- [[Strip]] — `ready` — 买 2 put + 买 1 call；偏空的跨式变体

## 日历策略 / Calendar Spread

Category status: `ready`. topic474 #12 (sell near, buy far, same strike).

- [[Long Call Calendar Spread]] — `ready`
- [[Long Put Calendar Spread]] — `ready`

## 对角策略 / Diagonal Spread

Category status: `ready` for structure. Wikipedia dedicated page; OIC calendar only as the “different-strike variation” note. No single published P/L formula.

- [[Diagonal Call Spread]] — `ready` — 不同执行价 + 不同到期；盈亏要按具体组合单独看

## 蝶式策略 / Butterfly

Category status: `ready`. topic474 #5 (call or put).

- [[Long Call Butterfly]] — `ready`
- [[Long Put Butterfly]] — `ready`

## 鹰式策略 / Condor

Category status: `ready`. topic474 #6 (call or put).

- [[Long Call Condor]] — `ready`
- [[Long Put Condor]] — `ready`

## 铁蝶式策略 / Iron Butterfly

Category status: `ready`. App menu; not in topic474.

- [[Short Iron Butterfly]] — `ready`

## 铁鹰式策略 / Iron Condor

Category status: `ready`. topic474 #7.

- [[Short Condor (Iron Condor)]] — `ready`
