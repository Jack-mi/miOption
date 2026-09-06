---
type: entity
title: Bear Put Spread
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - entity
  - strategy
  - vertical-spread
entity_type: option-strategy
aliases:
  - bear put spread
  - debit put spread
  - vertical put debit
sources:
  - "[[Source — Bear Put Spread]]"
related: []
---

# Bear Put Spread

Express a moderately bearish view with defined risk and reward by offsetting long-put cost with a short lower put.

- Underlying: equity option
- Knowledge id: `strategy.bear_put_spread`
- Review status: `published`
- Futu category: 垂直策略 / Vertical Spread

## Legs

- long higher-strike put (put option)
- short lower-strike put, same expiration (put option)

## Meaning

Express a moderately bearish view with defined risk and reward by offsetting long-put cost with a short lower put.

## Scenario

Moderately bearish; expects a decline toward or below the short put strike by expiration.

For bearish investors who want defined risk and are willing to cap downside gains.

## Method

- Maximum profit: The maximum gain is limited. The best that can happen is for the stock price to be below the lower strike at expiration.
- Maximum loss: The maximum loss is limited. The worst that can happen at expiration is for the stock to be above the higher (long put) strike price.
- Break-even: This strategy breaks even if, at expiration, the stock price is below the upper strike by the amount of the initial outlay (the debit). In that case, the short put would expire worthless, and the long put's intrinsic value would equal the debit.
- Assignment / expiration: Yes. Early assignment, while possible at any time, generally occurs only when a put option goes deep into-the-money. Yes. If held into expiration, this strategy entails added risk.

## How the price reacts to volatility and time

- Volatility: Slight, all other things being equal. Since the strategy involves being short one put and long another with the same expiration, the effects of volatility shifts on the two contracts may offset each other to a large degree.
- Time decay: The passage of time hurts the position, though not quite as much as it does an plain long put position. Since the strategy involves being long one put and short another with the same expiration, the effects of time decay on the two contracts may offset each other to a large degree.

## Evidence

### Definition

- [[Source — Bear Put Spread]] · `Bear Put Spread` · lines 1–4
  > A bear put spread consists of buying one put and selling another put, at a lower strike, to offset part of the upfront cost.
- [[Source — Bear Put Spread]] · `Description` · lines 5–16
  > A bear put spread is a type of vertical spread. It consists of buying one put in hopes of profiting from a decline in the underlying stock, and writing another put with the same expiration, but with a lower strike price, as a way to offset some of the cost. Because of the way the strike prices are selected, this strate
- [[Source — Bear Put Spread]] · `Summary` · lines 40–43
  > A bear put spread consists of buying one put and selling another put, at a lower strike, to offset part of the upfront cost. The spread generally profits if the stock price moves lower. The potential profit is limited, but so is the risk should the stock unexpectedly rally.

### Legs

- [[Source — Bear Put Spread]] · `Example` · lines 17–33
  > - Long 1 XYZ 60 put - Short 1 XYZ 55 put MAXIMUM GAIN - High strike - low strike - net premium paid MAXIMUM LOSS - Net premium paid The lower the short put strike, the higher the potential maximum profit; but that benefit has to be weighed against the disadvantage: a smaller amount of premium received. It is interestin

### Objective

- [[Source — Bear Put Spread]] · `Description` · lines 5–16
  > A bear put spread is a type of vertical spread. It consists of buying one put in hopes of profiting from a decline in the underlying stock, and writing another put with the same expiration, but with a lower strike price, as a way to offset some of the cost. Because of the way the strike prices are selected, this strate
- [[Source — Bear Put Spread]] · `Motivation` · lines 44–47
  > Profit from a near-term decline in the underlying stock.

### Market Outlook

- [[Source — Bear Put Spread]] · `Outlook` · lines 34–39
  > Looking for a steady or declining stock price during the term of the options. While the longer-term outlook is secondary, there is an argument for considering another alternative if the investor is bearish on the stock's future. It would take careful pinpointing to forecast when an expected rally would end and the even

### Max Gain

- [[Source — Bear Put Spread]] · `Example` · lines 17–33
  > - Long 1 XYZ 60 put - Short 1 XYZ 55 put MAXIMUM GAIN - High strike - low strike - net premium paid MAXIMUM LOSS - Net premium paid The lower the short put strike, the higher the potential maximum profit; but that benefit has to be weighed against the disadvantage: a smaller amount of premium received. It is interestin
- [[Source — Bear Put Spread]] · `Max Gain` · lines 56–59
  > The maximum gain is limited. The best that can happen is for the stock price to be below the lower strike at expiration. The upper limit of profitability is reached at that point, even if the stock were to decline further. Assuming the stock price is below both strike prices at expiration, the investor would exercise t

### Max Loss

- [[Source — Bear Put Spread]] · `Example` · lines 17–33
  > - Long 1 XYZ 60 put - Short 1 XYZ 55 put MAXIMUM GAIN - High strike - low strike - net premium paid MAXIMUM LOSS - Net premium paid The lower the short put strike, the higher the potential maximum profit; but that benefit has to be weighed against the disadvantage: a smaller amount of premium received. It is interestin
- [[Source — Bear Put Spread]] · `Max Loss` · lines 52–55
  > The maximum loss is limited. The worst that can happen at expiration is for the stock to be above the higher (long put) strike price. In that case, both put options expire worthless, and the loss incurred is simply the initial outlay for the position (the debit).

### Breakeven

- [[Source — Bear Put Spread]] · `Breakeven` · lines 66–71
  > This strategy breaks even if, at expiration, the stock price is below the upper strike by the amount of the initial outlay (the debit). In that case, the short put would expire worthless, and the long put's intrinsic value would equal the debit. Breakeven = long put strike - net debit paid

### Volatility Effect

- [[Source — Bear Put Spread]] · `Volatility` · lines 72–77
  > Slight, all other things being equal. Since the strategy involves being short one put and long another with the same expiration, the effects of volatility shifts on the two contracts may offset each other to a large degree. Note, however, that the stock price can move in such a way that a volatility change would affect

### Time Decay Effect

- [[Source — Bear Put Spread]] · `Time Decay` · lines 78–83
  > The passage of time hurts the position, though not quite as much as it does an plain long put position. Since the strategy involves being long one put and short another with the same expiration, the effects of time decay on the two contracts may offset each other to a large degree. Regardless of the theoretical impact

### Assignment Or Expiration Risk

- [[Source — Bear Put Spread]] · `Assignment Risk` · lines 84–89
  > Yes. Early assignment, while possible at any time, generally occurs only when a put option goes deep into-the-money. Be warned, however, that using the long put to cover the short put assignment will require financing a long stock position for one business day. And be aware, any situation where a stock is involved in a
- [[Source — Bear Put Spread]] · `Expiration Risk` · lines 90–97
  > Yes. If held into expiration, this strategy entails added risk. The investor cannot know for sure until the following Monday whether or not the short put was assigned. The problem is most acute if the stock is trading just below, at or just above the short put strike. Guessing wrong either way could be costly. Assume t

### Suitability Constraints

- [[Source — Bear Put Spread]] · `Motivation` · lines 44–47
  > Profit from a near-term decline in the underlying stock.
- [[Source — Bear Put Spread]] · `Comments` · lines 98–101
  > N/A


See the [[index|Wiki Index]].
