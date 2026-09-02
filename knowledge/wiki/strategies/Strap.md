---
type: entity
title: Strap
status: developing
created: 2026-09-02
updated: 2026-09-02
tags:
  - entity
  - strategy
  - strap
entity_type: option-strategy
aliases:
  - 带式策略
  - strap strategy
sources:
  - "[[Source — Futu 常用期权组合简介]]"
related:
  - "[[Long Straddle]]"
  - "[[Strip]]"
---

# Strap

A long-volatility combination with a bullish tilt: two long calls and one long put, same expiration and same strike.

- Underlying: equity option
- Knowledge id: `strategy.strap`
- Review status: `reviewed`
- Futu category: 带式策略 / Strap (topic474 #8)

> Developing: OIC has no standalone Strap page. Legs and meaning are from Futu's help article. Do not treat P/L numbers as published until a dedicated text source exists.

## Legs

- long two call options, same strike and expiration
- long one put option, same strike and expiration

## Meaning

买入两个看涨期权并买入一个看跌期权，期权的到期日和行权价均相同。

This is a straddle with an extra long call, so a large up-move pays more than a large down-move of the same size, at a higher net debit than a 1x1 straddle.

## Scenario

Expect a large move, with the larger payoff preferred on the upside.

## Method

- Max gain: Not published. No dedicated OIC P/L page.
- Max loss: Not published. Limited in principle to the net premium paid for the three long options.
- Breakeven: Not published.
- Assignment / expiration: Long options only; the holder chooses exercise. No short-leg assignment.

## Evidence

- [[Source — Futu 常用期权组合简介]] · `Strap`
  > 买入两个看涨期权并买入一个看跌期权，期权的到期日和行权价均相同。

## See also

- related to: [[Long Straddle]]
- related to: [[Strip]]

See the [[index|Wiki Index]].
