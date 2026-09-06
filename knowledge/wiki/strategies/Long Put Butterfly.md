---
type: entity
title: Long Put Butterfly
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - entity
  - strategy
  - butterfly
entity_type: option-strategy
aliases:
  - long put butterfly
  - put butterfly
sources:
  - "[[Source — Long Put Butterfly]]"
  - "[[Source — Futu 常用期权组合简介]]"
related:
  - "[[Long Call Butterfly]]"
---

# Long Put Butterfly

Profit if the underlying finishes near the body strike at expiration, with defined risk equal to the net debit. Same expiration payoff as a call butterfly with the same strikes.

- Underlying: equity option
- Knowledge id: `strategy.long_put_butterfly`
- Review status: `published`
- Futu category: 蝶式策略 / Butterfly (topic474 #5)

## Legs

- long one lower-strike wing (put option)
- short two middle-strike body puts (put option)
- long one upper-strike wing, equidistant, same expiration (put option)

## Meaning

A long put butterfly is composed of two short puts at a middle strike, and long one put each at a lower and a higher strike.

## Scenario

The investor is looking for the underlying stock to achieve a specific price target at expiration.

For investors seeking defined-risk short-volatility style payoff who accept high expiration pin risk at the body.

## Method

- Maximum profit: The maximum gain would occur should the underlying stock be at the middle strike at expiration. In that case, the long put with the upper strike would be in-the-money and all the other options would expire worthless.
- Maximum loss: The maximum loss would occur should the underlying stock be outside the wings at expiration. If the stock were above the upper strike all the options would expire worthless; if below the lower strike all the options would be exercised and offset each other for a zero profit.
- Break-even: The strategy breaks even if at expiration the underlying stock is above the lower strike or below the upper strike by the amount of the premium paid to initiate the position.
- Assignment / expiration: The short puts that form the body are subject to exercise at any time. This strategy has an extremely high expiration risk at the body.

## How the price reacts to volatility and time

- Volatility: An increase in implied volatility, all other things equal, will usually have a slightly negative impact on this strategy.
- Time decay: The passage of time, all other things equal, will usually have a positive impact if the body is at-the-money, and a negative impact if the body is away from the money.

## Evidence

### Definition

- [[Source — Long Put Butterfly]] · `Description`
  > A long put butterfly is composed of two short puts at a middle strike, and long one put each at a lower and a higher strike. The upper and lower strikes (wings) must both be equidistant from the middle strike (body), and all the options must be the same expiration.
- [[Source — Futu 常用期权组合简介]] · `Butterfly spread`
  > 买入一个行权价较低的看涨期权（看跌期权）和一个行权价较高的看涨期权（看跌期权），卖出两个行权价在中间的看涨期权（看跌期权），三个期权的到期日相同。

### Legs

- [[Source — Long Put Butterfly]] · `Example`
  > Long 1 XYZ 65 put / Short 2 XYZ 60 puts / Long 1 XYZ 55 put

## See also

- related to: [[Long Call Butterfly]]

See the [[index|Wiki Index]].
