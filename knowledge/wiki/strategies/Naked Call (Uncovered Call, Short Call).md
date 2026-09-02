---
type: entity
title: "Naked Call (Uncovered Call, Short Call)"
status: evergreen
created: 2026-09-02
updated: 2026-09-02
tags:
  - entity
  - strategy
  - single-option
entity_type: option-strategy
aliases:
  - naked call
  - uncovered call
  - short call
sources:
  - "[[Source — Naked Call (Uncovered Call, Short Call)]]"
related:
  - "[[Naked Put (Uncovered Put, Short Put)]]"
---

# Naked Call (Uncovered Call, Short Call)

Collect premium income when expecting the underlying to stay flat or fall, accepting theoretically unlimited upside risk.

- Underlying: equity option
- Knowledge id: `strategy.naked_call`
- Review status: `published`
- Futu category: 单腿期权 / Single Option

## Legs

- short one uncovered call (call option)

## Meaning

Collect premium income when expecting the underlying to stay flat or fall, accepting theoretically unlimited upside risk.

## Scenario

Neutral to bearish; does not want a sharp rally.

Only for investors who can post margin and accept theoretically unlimited loss if the stock rises sharply.

## Method

- Max gain: The maximum gain is very limited. The best that can happen is for expiration to arrive with the stock price below the strike price.
- Max loss: The maximum loss is unlimited. The worst that can happen is for the stock to rise to infinity, in which case the investor would have to buy stock in the market at that undefinably high price and sell it at the strike price.
- Breakeven: At expiration, the strategy breaks even if the stock price is above the strike price by the amount of the premium received; i.e., the option's intrinsic value equals the price at which the option was sold. Breakeven = strike + premium
- Assignment / expiration: There is tremendous assignment risk. Early assignment, while possible at any time, generally occurs only when the stock goes ex-dividend. The option writer cannot know until the Monday following expiration whether or not assignment occurred. And unless the investor is prepared (and approved) to hold a short stock position that is already 'under water' at the strike price, the goal is to buy back the assigned stock as soon as possible.

## Greeks and time

- Volatility: An increase in implied volatility would have a negative impact on this strategy, all other things equal. It means the market perceives there to be a greater chance than before of the option becoming in-the-money or more in-the-money.
- Time decay: The passage of time will have an extremely positive impact on this strategy, all other things equal. As expiration approaches, option values tend to decline toward their intrinsic value.

## Evidence

### Definition

- [[Source — Naked Call (Uncovered Call, Short Call)]] · `Naked Call (Uncovered Call, Short Call)` · lines 1–4
  > This strategy consists of writing an uncovered call option.
- [[Source — Naked Call (Uncovered Call, Short Call)]] · `Description` · lines 5–14
  > An investor who writes a call option without owning the underlying stock is banking on a flat to bearish short-term forecast for the stock. The strategy consists of writing the call in hopes that it will lose value through time decay and eventually expire out-of-the-money. If the term ends without the option being assi
- [[Source — Naked Call (Uncovered Call, Short Call)]] · `Summary` · lines 33–36
  > This strategy consists of writing an uncovered call option. It profits if the stock price holds steady or declines, and does best if the option expires worthless.

### Legs

- [[Source — Naked Call (Uncovered Call, Short Call)]] · `Example` · lines 15–26
  > - Short 1 XYZ 60 call MAXIMUM GAIN - Premium received MAXIMUM LOSS - Unlimited

### Objective

- [[Source — Naked Call (Uncovered Call, Short Call)]] · `Description` · lines 5–14
  > An investor who writes a call option without owning the underlying stock is banking on a flat to bearish short-term forecast for the stock. The strategy consists of writing the call in hopes that it will lose value through time decay and eventually expire out-of-the-money. If the term ends without the option being assi
- [[Source — Naked Call (Uncovered Call, Short Call)]] · `Motivation` · lines 37–40
  > The only motive for writing an uncovered call option is to earn income from selling premium.

### Market Outlook

- [[Source — Naked Call (Uncovered Call, Short Call)]] · `Outlook` · lines 27–32
  > Looking for a steady or falling stock price during life of the option. In principle, an investor who expects an imminent and severe downturn could write a naked call despite being bullish on the stock's long term prospects. However, success would require being right about the extent and exact timing of the short-term c

### Max Gain

- [[Source — Naked Call (Uncovered Call, Short Call)]] · `Example` · lines 15–26
  > - Short 1 XYZ 60 call MAXIMUM GAIN - Premium received MAXIMUM LOSS - Unlimited
- [[Source — Naked Call (Uncovered Call, Short Call)]] · `Max Gain` · lines 49–52
  > The maximum gain is very limited. The best that can happen is for expiration to arrive with the stock price below the strike price. In that case, the option expires worthless and the investor pockets the premium received for selling the call option.

### Max Loss

- [[Source — Naked Call (Uncovered Call, Short Call)]] · `Example` · lines 15–26
  > - Short 1 XYZ 60 call MAXIMUM GAIN - Premium received MAXIMUM LOSS - Unlimited
- [[Source — Naked Call (Uncovered Call, Short Call)]] · `Max Loss` · lines 45–48
  > The maximum loss is unlimited. The worst that can happen is for the stock to rise to infinity, in which case the investor would have to buy stock in the market at that undefinably high price and sell it at the strike price.

### Breakeven

- [[Source — Naked Call (Uncovered Call, Short Call)]] · `Breakeven` · lines 59–64
  > At expiration, the strategy breaks even if the stock price is above the strike price by the amount of the premium received; i.e., the option's intrinsic value equals the price at which the option was sold. Breakeven = strike + premium

### Volatility Effect

- [[Source — Naked Call (Uncovered Call, Short Call)]] · `Volatility` · lines 65–68
  > An increase in implied volatility would have a negative impact on this strategy, all other things equal. It means the market perceives there to be a greater chance than before of the option becoming in-the-money or more in-the-money. And even if the naked call writer weren't worried about that assessment, a higher call

### Time Decay Effect

- [[Source — Naked Call (Uncovered Call, Short Call)]] · `Time Decay` · lines 69–72
  > The passage of time will have an extremely positive impact on this strategy, all other things equal. As expiration approaches, option values tend to decline toward their intrinsic value. If, as hoped, the call is out-of-the-money, its intrinsic value is zero, and barring other developments it becomes increasingly likel

### Assignment Or Expiration Risk

- [[Source — Naked Call (Uncovered Call, Short Call)]] · `Assignment Risk` · lines 73–80
  > There is tremendous assignment risk. Early assignment, while possible at any time, generally occurs only when the stock goes ex-dividend. Unless they are completely indifferent to being assigned, investors with short positions must continuously monitor the stock for possible early assignment. A naked call writer is by
- [[Source — Naked Call (Uncovered Call, Short Call)]] · `Expiration Risk` · lines 81–84
  > The option writer cannot know until the Monday following expiration whether or not assignment occurred. And unless the investor is prepared (and approved) to hold a short stock position that is already 'under water' at the strike price, the goal is to buy back the assigned stock as soon as possible. The delay of a week

### Suitability Constraints

- [[Source — Naked Call (Uncovered Call, Short Call)]] · `Motivation` · lines 37–40
  > The only motive for writing an uncovered call option is to earn income from selling premium.
- [[Source — Naked Call (Uncovered Call, Short Call)]] · `Comments` · lines 85–88
  > This is the riskiest option strategy there is, and definitely not suitable for most investors. It requires posting a significant cash margin to initiate the transaction, but the risk is well in excess of that initial margin, and an unfavorable market move could force the investor to post additional margin on very short

## See also

- related to: [[Naked Put (Uncovered Put, Short Put)]]

See the [[index|Wiki Index]].
