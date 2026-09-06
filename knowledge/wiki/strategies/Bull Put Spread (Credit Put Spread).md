---
type: entity
title: Bull Put Spread (Credit Put Spread)
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - entity
  - strategy
  - vertical-spread
entity_type: option-strategy
aliases:
  - bull put spread
  - credit put spread
sources:
  - "[[Source — Bull Put Spread (Credit Put Spread)]]"
related: []
---

# Bull Put Spread (Credit Put Spread)

Collect a net credit when expecting the stock to stay above the short put strike, with downside risk capped by the long put.

- Underlying: equity option
- Knowledge id: `strategy.bull_put_spread`
- Review status: `published`
- Futu category: 垂直策略 / Vertical Spread

## Legs

- short higher-strike put (put option)
- long lower-strike put, same expiration (put option)

## Meaning

Collect a net credit when expecting the stock to stay above the short put strike, with downside risk capped by the long put.

## Scenario

Neutral to bullish; does not want the stock below the short put at expiration.

For investors seeking premium income with defined maximum loss equal to the width minus credit.

## Method

- Maximum profit: The maximum gain is limited. The best that can happen is for the stock to be above the higher strike price at expiration.
- Maximum loss: The maximum loss is limited. The worst that can happen is for the stock price to be below the lower strike at expiration.
- Break-even: This strategy breaks even if, at expiration, the stock price is below the upper strike (short put strike) by the amount of the initial credit received. In that case, the long put would expire worthless, and the short put's intrinsic value would equal the net credit.
- Assignment / expiration: Yes. Early assignment, while possible at any time, generally occurs only when a put option goes deep into-the-money. Yes. If held into expiration, this strategy entails added risk.

## How the price reacts to volatility and time

- Volatility: Slight, all other things being equal. Since the strategy involves being short one put and long another with the same expiration, the effects of volatility shifts on the two contracts may offset each other to a large degree.
- Time decay: The passage of time helps the position, though not quite as much as it does a plain short put position. Since the strategy involves being short one put and long another with the same expiration, the effects of time decay on the two contracts may offset each other to a large degree.

## Evidence

### Definition

- [[Source — Bull Put Spread (Credit Put Spread)]] · `Bull Put Spread (Credit Put Spread)` · lines 1–4
  > A bull put spread is a limited-risk, limited-reward strategy, consisting of a short put option and a long put option with a lower strike.
- [[Source — Bull Put Spread (Credit Put Spread)]] · `Description` · lines 5–16
  > A bull put spread involves being short a put option and long another put option with the same expiration but with a lower strike. The short put generates income, whereas the long put's main purpose is to offset assignment risk and protect the investor in case of a sharp move downward. Because of the relationship betwee
- [[Source — Bull Put Spread (Credit Put Spread)]] · `Summary` · lines 38–41
  > A bull put spread is a limited-risk, limited-reward strategy, consisting of a short put option and a long put option with a lower strike. This spread generally profits if the stock price holds steady or rises.

### Legs

- [[Source — Bull Put Spread (Credit Put Spread)]] · `Example` · lines 17–31
  > - Short 1 XYZ 60 put - Long 1 XYZ 55 put MAXIMUM GAIN - Net premium received MAXIMUM LOSS - High strike - low strike - net premium received The bull call spread requires a known initial outlay for an unknown eventual return; the bull put spread produces a known initial cash inflow in exchange for a possible outlay late

### Objective

- [[Source — Bull Put Spread (Credit Put Spread)]] · `Description` · lines 5–16
  > A bull put spread involves being short a put option and long another put option with the same expiration but with a lower strike. The short put generates income, whereas the long put's main purpose is to offset assignment risk and protect the investor in case of a sharp move downward. Because of the relationship betwee
- [[Source — Bull Put Spread (Credit Put Spread)]] · `Motivation` · lines 42–45
  > Investors initiate this spread either as a way to earn income with limited risk, or to profit from a rise in the underlying stock's price, or both.

### Market Outlook

- [[Source — Bull Put Spread (Credit Put Spread)]] · `Outlook` · lines 32–37
  > Looking for a rise in the underlying stock's price during the options' term.​ While the longer-term outlook is secondary, there is an argument for considering another alternative if the investor is bullish on the stock's future. It would take careful pinpointing to forecast when an expected decline would end and the ev

### Max Gain

- [[Source — Bull Put Spread (Credit Put Spread)]] · `Example` · lines 17–31
  > - Short 1 XYZ 60 put - Long 1 XYZ 55 put MAXIMUM GAIN - Net premium received MAXIMUM LOSS - High strike - low strike - net premium received The bull call spread requires a known initial outlay for an unknown eventual return; the bull put spread produces a known initial cash inflow in exchange for a possible outlay late
- [[Source — Bull Put Spread (Credit Put Spread)]] · `Max Gain` · lines 54–57
  > The maximum gain is limited. The best that can happen is for the stock to be above the higher strike price at expiration. In that case, both put options expire worthless, and the investor pockets the credit received when putting on the position.

### Max Loss

- [[Source — Bull Put Spread (Credit Put Spread)]] · `Example` · lines 17–31
  > - Short 1 XYZ 60 put - Long 1 XYZ 55 put MAXIMUM GAIN - Net premium received MAXIMUM LOSS - High strike - low strike - net premium received The bull call spread requires a known initial outlay for an unknown eventual return; the bull put spread produces a known initial cash inflow in exchange for a possible outlay late
- [[Source — Bull Put Spread (Credit Put Spread)]] · `Max Loss` · lines 50–53
  > The maximum loss is limited. The worst that can happen is for the stock price to be below the lower strike at expiration. In that case, the investor will be assigned on the short put, now deep-in-the-money, and will exercise their long put. The simultaneous exercise and assignment will mean buying the stock at the high

### Breakeven

- [[Source — Bull Put Spread (Credit Put Spread)]] · `Breakeven` · lines 64–69
  > This strategy breaks even if, at expiration, the stock price is below the upper strike (short put strike) by the amount of the initial credit received. In that case, the long put would expire worthless, and the short put's intrinsic value would equal the net credit. Breakeven = short put strike - net credit received

### Volatility Effect

- [[Source — Bull Put Spread (Credit Put Spread)]] · `Volatility` · lines 70–75
  > Slight, all other things being equal. Since the strategy involves being short one put and long another with the same expiration, the effects of volatility shifts on the two contracts may offset each other to a large degree. Note, however, that the stock price can move in such a way that a volatility change would affect

### Time Decay Effect

- [[Source — Bull Put Spread (Credit Put Spread)]] · `Time Decay` · lines 76–81
  > The passage of time helps the position, though not quite as much as it does a plain short put position. Since the strategy involves being short one put and long another with the same expiration, the effects of time decay on the two contracts may offset each other to a large degree. Regardless of the theoretical impact

### Assignment Or Expiration Risk

- [[Source — Bull Put Spread (Credit Put Spread)]] · `Assignment Risk` · lines 82–87
  > Yes. Early assignment, while possible at any time, generally occurs only when a put option goes deep into-the-money. Be warned, however, that using the long put to cover the short put assignment will require financing a long stock position for one business day. And be aware, a situation where a stock is involved in a r
- [[Source — Bull Put Spread (Credit Put Spread)]] · `Expiration Risk` · lines 88–97
  > Yes. If held into expiration, this strategy entails added risk. The investor cannot know for sure whether or not they will be assigned on the short put until the Monday after expiration. The problem is most acute if the stock is trading just below, at or just above the short put strike. Say, the short put ends up sligh

### Suitability Constraints

- [[Source — Bull Put Spread (Credit Put Spread)]] · `Motivation` · lines 42–45
  > Investors initiate this spread either as a way to earn income with limited risk, or to profit from a rise in the underlying stock's price, or both.


See the [[index|Wiki Index]].
