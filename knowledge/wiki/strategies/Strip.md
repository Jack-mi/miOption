---
type: entity
title: Strip
status: developing
created: 2026-09-02
updated: 2026-09-02
tags:
  - entity
  - strategy
  - strip
entity_type: option-strategy
aliases:
  - 条式策略
  - strip strategy
sources:
  - "[[Source — Futu 常用期权组合简介]]"
related:
  - "[[Long Straddle]]"
  - "[[Strap]]"
---

# Strip

A long-volatility combination with a bearish tilt: two long puts and one long call, same expiration and same strike.

- Underlying: equity option
- Knowledge id: `strategy.strip`
- Review status: `reviewed`
- Futu category: 条式策略 / Strip (topic474 #9)

> Developing: OIC has no standalone Strip page. Legs and meaning are from Futu's help article. Do not treat P/L numbers as published until a dedicated text source exists.

## Legs

- long two put options, same strike and expiration
- long one call option, same strike and expiration

## Meaning

买入两个看跌期权并买入一个看涨期权，期权的到期日和行权价均相同。

This is a straddle with an extra long put, so a large down-move pays more than a large up-move of the same size, at a higher net debit than a 1x1 straddle.

## Scenario

Expect a large move, with the larger payoff preferred on the downside.

## Method

- Max gain: Not published. No dedicated OIC P/L page.
- Max loss: Not published. Limited in principle to the net premium paid for the three long options.
- Breakeven: Not published.
- Assignment / expiration: Long options only; the holder chooses exercise. No short-leg assignment.

## Evidence

- [[Source — Futu 常用期权组合简介]] · `Strip`
  > 买入两个看跌期权并买入一个看涨期权，期权的到期日和行权价均相同。

## See also

- related to: [[Long Straddle]]
- related to: [[Strap]]

See the [[index|Wiki Index]].
