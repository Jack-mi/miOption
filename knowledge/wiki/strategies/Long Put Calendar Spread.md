---
type: entity
title: Long Put Calendar Spread
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - entity
  - strategy
  - calendar-spread
entity_type: option-strategy
aliases:
  - put calendar
  - put horizontal
  - long put time spread
sources:
  - "[[Source — Long Put Calendar Spread (Put Horizontal)]]"
  - "[[Source — Futu 常用期权组合简介]]"
related:
  - "[[Long Call Calendar Spread]]"
  - "[[Diagonal Call Spread]]"
---

# Long Put Calendar Spread

Sell a near-term put and buy a longer-dated put, typically the same strike. Near-term neutral to slightly bullish, then longer-term bearish.

- Underlying: equity option
- Knowledge id: `strategy.long_put_calendar`
- Review status: `published`
- Futu category: 日历策略 / Calendar Spread (topic474 #12)

## Legs

- short near-term put (put option)
- long longer-dated put, typically same strike (put option)

## Meaning

To enter into a long put calendar spread, an investor sells one near-term put option and buys a second put option with a more distant expiration.

## Scenario

The investor is looking for either a steady to slightly rising stock price during the life of the near-term option and then a move lower during the life of the far-term option, or a sharp rise in implied volatility levels.

## Method

- Maximum profit: At the expiration of the near-term option, the maximum gain would occur should the underlying stock be at the strike price of the expiring option. After that, the position is a long put.
- Maximum loss: The maximum loss would occur should the two options reach parity. The loss would be the premium paid to establish the position.
- Break-even: A function of stock price, implied volatility, and time decay while both options are live. If the near-term put expires worthless, later breakeven is the strike minus the net debit.
- Assignment / expiration: Early assignment generally occurs for a put when it goes deep-in-the-money. Assignment on the near-term put leaves a long stock position hedged by the longer-term put.

## How the price reacts to volatility and time

- Volatility: An increase in implied volatility, all other things equal, would have an extremely positive impact on this strategy.
- Time decay: Positive while the near-term put is decaying faster; after it expires the remaining long put is hurt by time decay.

## Evidence

### Definition

- [[Source — Long Put Calendar Spread (Put Horizontal)]] · `Description`
  > To enter into a long put calendar spread, an investor sells one near-term put option and buys a second put option with a more distant expiration. The strategy most commonly involves puts with the same strike (horizontal spread), but can also be done with different strikes (diagonal spread).
- [[Source — Futu 常用期权组合简介]] · `Calendar spread`
  > 卖出一个到期日较近的期权并买入一个到期日较远的期权，两个期权的行权价相同。

### Legs

- [[Source — Long Put Calendar Spread (Put Horizontal)]] · `Example`
  > Short 1 XYZ near 60 put / Long 1 XYZ far 60 put

## See also

- related to: [[Long Call Calendar Spread]]
- related to: [[Diagonal Call Spread]]

See the [[index|Wiki Index]].
