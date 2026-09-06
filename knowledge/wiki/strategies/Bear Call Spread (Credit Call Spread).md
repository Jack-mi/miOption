---
type: entity
title: Bear Call Spread (Credit Call Spread)
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - entity
  - strategy
  - vertical-spread
entity_type: option-strategy
aliases:
  - bear call spread
  - credit call spread
sources:
  - "[[Source — Bear Call Spread (Credit Call Spread)]]"
related: []
---

# Bear Call Spread (Credit Call Spread)

Collect a net credit when expecting the stock to stay below the short call strike, with upside risk capped by the long call.

- Underlying: equity option
- Knowledge id: `strategy.bear_call_spread`
- Review status: `published`
- Futu category: 垂直策略 / Vertical Spread

## Legs

- short lower-strike call (call option)
- long higher-strike call, same expiration (call option)

## Meaning

Collect a net credit when expecting the stock to stay below the short call strike, with upside risk capped by the long call.

## Scenario

Neutral to bearish; does not want the stock above the short call at expiration.

For investors seeking premium income with defined maximum loss equal to the width minus credit.

## Method

- Maximum profit: The maximum gain is limited. The best that can happen at expiration is for the stock to be below both strike prices.
- Maximum loss: The maximum loss is limited. The worst that can happen at expiration is for the stock price to be above the higher strike.
- Break-even: This strategy breaks even at expiration if the stock price is above the lower strike by the amount of the initial credit received. In that case the long call would expire worthless, and the short call's intrinsic value would equal the net credit.
- Assignment / expiration: Yes. Early assignment, while possible at any time, generally occurs when the stock goes ex-dividend. Yes. The investor cannot know for sure whether or not they were assigned on the short call until the Monday after expiration.

## How the price reacts to volatility and time

- Volatility: Slight, all other things being equal. Since the strategy involves being short one call and long another with the same expiration, the effects of volatility shifts on the two contracts may offset each other to a large degree.
- Time decay: The passage of time helps the position, though not quite as much as it does a plain short call position. Since the strategy involves being short one call and long another with the same expiration, the effects of time decay on the two contracts may offset each other to a large degree.

## Evidence

### Definition

- [[Source — Bear Call Spread (Credit Call Spread)]] · `Bear Call Spread (Credit Call Spread)` · lines 1–4
  > A bear call spread is a limited-risk, limited-reward strategy, consisting of one short call option.
- [[Source — Bear Call Spread (Credit Call Spread)]] · `Description` · lines 5–20
  > A bear call spread is a type of vertical spread. It contains two calls with the same expiration but different strikes. The strike price of the short call is below the strike of the long call, which means this strategy will always generate a net cash inflow (net credit) at the outset. The short call's main purpose is to
- [[Source — Bear Call Spread (Credit Call Spread)]] · `Summary` · lines 40–45
  > A bear call spread is a limited-risk, limited-reward strategy, consisting of one short call option and one long call option. This strategy generally profits if the stock price holds steady or declines. The most it can generate is the net premium received at the outset. If the forecast is wrong and the stock rallies ins

### Legs

- [[Source — Bear Call Spread (Credit Call Spread)]] · `Example` · lines 21–35
  > - Short 1 XYZ 60 call - Long 1 XYZ 65 call MAXIMUM GAIN - Net premium received MAXIMUM LOSS - High strike - low strike - net premium received The chief difference is the timing of the cash flows. The bear put spread requires a known initial outlay for an unknown eventual return; the bear call spread produces a known in

### Objective

- [[Source — Bear Call Spread (Credit Call Spread)]] · `Description` · lines 5–20
  > A bear call spread is a type of vertical spread. It contains two calls with the same expiration but different strikes. The strike price of the short call is below the strike of the long call, which means this strategy will always generate a net cash inflow (net credit) at the outset. The short call's main purpose is to
- [[Source — Bear Call Spread (Credit Call Spread)]] · `Motivation` · lines 46–49
  > The chance to earn income with limited risk, and/or profit from a decline in the underlying stock's price.

### Market Outlook

- [[Source — Bear Call Spread (Credit Call Spread)]] · `Outlook` · lines 36–39
  > Looking for a decline in the underlying stock's price during the life of the options. As with any limited-time strategy, the investor's long-term forecast for the underlying stock isn't as important, but this is probably not a suitable choice for those who have a bearish outlook past the immediate future. It would take

### Max Gain

- [[Source — Bear Call Spread (Credit Call Spread)]] · `Example` · lines 21–35
  > - Short 1 XYZ 60 call - Long 1 XYZ 65 call MAXIMUM GAIN - Net premium received MAXIMUM LOSS - High strike - low strike - net premium received The chief difference is the timing of the cash flows. The bear put spread requires a known initial outlay for an unknown eventual return; the bear call spread produces a known in
- [[Source — Bear Call Spread (Credit Call Spread)]] · `Max Gain` · lines 58–61
  > The maximum gain is limited. The best that can happen at expiration is for the stock to be below both strike prices. In that case, both the short and long call options expire worthless, and the investor pockets the credit received when putting on the position.

### Max Loss

- [[Source — Bear Call Spread (Credit Call Spread)]] · `Example` · lines 21–35
  > - Short 1 XYZ 60 call - Long 1 XYZ 65 call MAXIMUM GAIN - Net premium received MAXIMUM LOSS - High strike - low strike - net premium received The chief difference is the timing of the cash flows. The bear put spread requires a known initial outlay for an unknown eventual return; the bear call spread produces a known in
- [[Source — Bear Call Spread (Credit Call Spread)]] · `Max Loss` · lines 54–57
  > The maximum loss is limited. The worst that can happen at expiration is for the stock price to be above the higher strike. In that case, the investor will be assigned on the short call, now deep-in-the-money, and will exercise the long call. The simultaneous exercise and assignment will mean selling the stock at the lo

### Breakeven

- [[Source — Bear Call Spread (Credit Call Spread)]] · `Breakeven` · lines 68–73
  > This strategy breaks even at expiration if the stock price is above the lower strike by the amount of the initial credit received. In that case the long call would expire worthless, and the short call's intrinsic value would equal the net credit. Breakeven = short call strike + net credit received

### Volatility Effect

- [[Source — Bear Call Spread (Credit Call Spread)]] · `Volatility` · lines 74–79
  > Slight, all other things being equal. Since the strategy involves being short one call and long another with the same expiration, the effects of volatility shifts on the two contracts may offset each other to a large degree. Note, however, that the stock price can move in such a way that a volatility change would affec

### Time Decay Effect

- [[Source — Bear Call Spread (Credit Call Spread)]] · `Time Decay` · lines 80–85
  > The passage of time helps the position, though not quite as much as it does a plain short call position. Since the strategy involves being short one call and long another with the same expiration, the effects of time decay on the two contracts may offset each other to a large degree. Regardless of the theoretical impac

### Assignment Or Expiration Risk

- [[Source — Bear Call Spread (Credit Call Spread)]] · `Assignment Risk` · lines 86–91
  > Yes. Early assignment, while possible at any time, generally occurs when the stock goes ex-dividend. Be warned, however, that using the long call to cover the short call assignment will require establishing a short stock position for one business day, due to the delay in receiving assignment notification. And be aware,
- [[Source — Bear Call Spread (Credit Call Spread)]] · `Expiration Risk` · lines 92–101
  > Yes. The investor cannot know for sure whether or not they were assigned on the short call until the Monday after expiration. That creates risk. The problem is most acute if the stock is trading just below, at or just above the short call strike. Say the short call ends up slightly in-the-money, and the investor buys t

### Suitability Constraints

- [[Source — Bear Call Spread (Credit Call Spread)]] · `Motivation` · lines 46–49
  > The chance to earn income with limited risk, and/or profit from a decline in the underlying stock's price.


See the [[index|Wiki Index]].
