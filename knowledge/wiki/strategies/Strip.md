---
type: entity
title: Strip
status: evergreen
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
  - "[[Source — Wikipedia Straddle]]"
  - "[[Source — Futu 常用期权组合简介]]"
related:
  - "[[Long Straddle]]"
  - "[[Strap]]"
---

# Strip

A long-volatility combination with a bearish tilt: two long puts and one long call, same expiration and same strike.

- Underlying: equity option
- Knowledge id: `strategy.strip`
- Review status: `published`
- Futu category: 条式策略 / Strip (topic474 #9)

Wikipedia and Futu agree on the legs and the bearish tilt. Neither publishes a numeric max gain, max loss, or breakeven for strip. Those three numbers stay blank rather than being borrowed from a 1x1 straddle.

## Legs

- long two put options, same strike and expiration
- long one call option, same strike and expiration

## Meaning

买入两个看跌期权并买入一个看涨期权，期权的到期日和行权价均相同。

Wikipedia: a strip is a modified straddle (one call and two puts at the same strike). Like a straddle it can profit from a large move either way; unlike a straddle it is more bearish.

## Scenario

Expect a large move, and treat a decrease as more likely than an increase.

## Method

- Max gain: Not published on Wikipedia or Futu. Wikipedia only says a strip can profit from a large move in either direction, more so if the move is down.
- Max loss: Not published on Wikipedia or Futu as a strip-specific number.
- Breakeven: Not published on Wikipedia or Futu.
- Assignment / expiration: All three options are long; the holder chooses exercise. No short-leg assignment.

## Evidence

- [[Source — Futu 常用期权组合简介]] · `Strip`
  > 买入两个看跌期权并买入一个看涨期权，期权的到期日和行权价均相同。
- [[Source — Wikipedia Straddle]] · `Straps and strips` · lines 20–22
  > Straps and strips are modified versions of a straddle. Whereas a straddle consists of one put and one call at the same strike price, a strap consists of two calls and one put at the same strike price, while a strip consists of one call and two puts. Like a straddle, a strap or a strip allows the trader to profit from a large move in either direction, but while a straddle is directionally neutral, a strap is more bullish (used by a trader who considers an increase more likely than a decrease), and a strip is more bearish (used by a trader who considers a decrease more likely than an increase).

## See also

- related to: [[Long Straddle]]
- related to: [[Strap]]

See the [[index|Wiki Index]].
