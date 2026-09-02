---
type: entity
title: Naked Put (Uncovered Put, Short Put)
status: evergreen
created: 2026-09-02
updated: 2026-09-02
tags:
  - entity
  - strategy
  - single-option
entity_type: option-strategy
aliases:
  - naked put
  - uncovered put
  - short put
sources:
  - "[[Source — Naked Put (Uncovered Put, Short Put)]]"
related:
  - "[[Naked Call (Uncovered Call, Short Call)]]"
  - "[[Cash-Secured Put]]"
---

# Naked Put (Uncovered Put, Short Put)

Write a put without reserved cash to buy the stock if assigned. Earn premium if the stock stays steady or rises; large loss if the stock falls toward zero.

- Underlying: equity option
- Knowledge id: `strategy.naked_put`
- Review status: `published`
- Futu category: 单腿期权 / Single Option

## Legs

- short one uncovered put (put option)

## Meaning

A naked put involves writing a put option without the reserved cash on hand to purchase the underlying stock.

## Scenario

Neutral to moderately bullish; expecting a steady or rising stock price and treating a decline as remote.

Not suitable for most investors: limited income, substantial downside, and assignment requires scrambling for cash.

## Method

- Max gain: Premium received. If the stock is above the strike at expiration, the put expires worthless.
- Max loss: Strike price minus premium received (substantial). Worst case is the stock falling to zero, forcing a purchase of worthless stock at the strike.
- Breakeven: At expiration, stock price below the strike by the premium received. Breakeven = strike – premium
- Assignment / expiration: Assignment is the chief worry; the writer has neither reserved cash nor a desire to own the stock. Early assignment generally occurs when the put goes deep in-the-money. After expiration the writer may not know assignment until the following Monday.

## Greeks and time

- Volatility: An increase in implied volatility would have a negative impact, including a higher cost to buy the put back.
- Time decay: Extremely positive. Passing days reduce the chance an OTM put finishes in-the-money.

## Evidence

### Definition

- [[Source — Naked Put (Uncovered Put, Short Put)]] · `Naked Put (Uncovered Put, Short Put)` · lines 1–3
  > A naked put involves writing a put option without the reserved cash on hand to purchase the underlying stock.
- [[Source — Naked Put (Uncovered Put, Short Put)]] · `Summary` · lines 29–33
  > A naked put involves writing a put option without the reserved cash on hand to purchase the underlying stock. This strategy entails a great deal of risk and relies on a steady or rising stock price. It does best if the option expires worthless.

### Legs

- [[Source — Naked Put (Uncovered Put, Short Put)]] · `Example` · lines 13–23
  > Short 1 XYZ 60 put MAXIMUM GAIN Premium received MAXIMUM LOSS Strike price - premium received (substantial)

### Objective

- [[Source — Naked Put (Uncovered Put, Short Put)]] · `Motivation` · lines 35–37
  > The only motive for writing an uncovered put is to earn premium income.

### Market Outlook

- [[Source — Naked Put (Uncovered Put, Short Put)]] · `Outlook` · lines 25–27
  > The investor is expecting a steady or rising stock price during life of option, and considers the likelihood of a decline very remote.

### Max Gain

- [[Source — Naked Put (Uncovered Put, Short Put)]] · `Max Gain` · lines 49–51
  > The maximum gains are very limited, especially relative to the extent of risk. If the position is still open at expiration, the best that can happen is for the stock price to be above the strike price. In that case, the option expires worthless and the investor pockets the premium received for selling the put option.

### Max Loss

- [[Source — Naked Put (Uncovered Put, Short Put)]] · `Max Loss` · lines 43–47
  > The maximum theoretical loss is limited, but it is very substantial. The worst that can happen is for the stock price to fall to zero, in which case the investor would be obligated to buy a worthless stock at the strike price. The effective purchase price, however, would be reduced somewhat by the premium received from selling the put option.

### Breakeven

- [[Source — Naked Put (Uncovered Put, Short Put)]] · `Breakeven` · lines 61–65
  > At expiration, the strategy breaks even if the stock price is below the strike price by the amount of the premium received, i.e., the option's intrinsic value equals the price at which the option was sold. Breakeven = strike – premium

### Volatility Effect

- [[Source — Naked Put (Uncovered Put, Short Put)]] · `Volatility` · lines 67–69
  > An increase in implied volatility would have a negative impact on this strategy, all other things being equal. Even if the investor felt that it had no correlation to a greater future risk of assignment, it would normally raise the cost of buying the put back to close out the position.

### Time Decay Effect

- [[Source — Naked Put (Uncovered Put, Short Put)]] · `Time Decay` · lines 71–75
  > The passage of time will have an extremely positive impact on this strategy, all other things equal. Every passing day diminishes the mathematical likelihood of an at-the-money or out-of-the-money put becoming in-the-money by expiration.

### Assignment Or Expiration Risk

- [[Source — Naked Put (Uncovered Put, Short Put)]] · `Assignment Risk` · lines 77–79
  > The risk of assignment, whether early or at expiration, is this investor's chief worry since the investor has neither the ready cash for this purpose nor a desire to own the underlying stock. A cautious selection of strike price and careful ongoing monitoring are the best ways to decrease the odds of a costly surprise, but buying to close the put is the only way to eliminate this risk. Early assignment, while possible at any time, generally occurs when the put option goes deep into-the-money.
- [[Source — Naked Put (Uncovered Put, Short Put)]] · `Expiration Risk` · lines 81–83
  > This risk applies, too. The option writer cannot know until the Monday following expiration whether assignment occurred or not. Since the goal is to resell the assigned stock as soon as possible, the delay of a weekend exposes the investor to interim stock price risk, as well as possible inconveniences in bridging the need for cash from option settlement until the subsequent stock sale settlement.

### Suitability Constraints

- [[Source — Naked Put (Uncovered Put, Short Put)]] · `Comments` · lines 85–87
  > This strategy is second only to naked calls in its level of risk, and not suitable for most investors. It requires posting a significant margin to initiate the transaction, but the risk is well in excess of that initial margin, and an unfavorable market move could force the investor to post additional margin on very short notice or to liquidate their position at a substantial loss.
- [[Source — Naked Put (Uncovered Put, Short Put)]] · `Variations` · lines 39–41
  > Cash-secured puts are the same as naked puts, but with two vital exceptions. First, the naked put writer has not set aside the cash to buy the stock if assigned. As a result, assignment would require urgent and possibly costly maneuvers to get hold of enough cash by settlement. Second, the naked put writer has no interest in acquiring the underlying stock. If assigned, the goal would be to resell the stock as quickly as possible to minimize the duration and risk of stock ownership.

## See also

- related to: [[Naked Call (Uncovered Call, Short Call)]]
- related to: [[Cash-Secured Put]]

See the [[index|Wiki Index]].
