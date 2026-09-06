---
type: entity
title: Long Call Calendar Spread
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - entity
  - strategy
  - calendar-spread
entity_type: option-strategy
aliases:
  - call calendar
  - call horizontal
  - time spread
sources:
  - "[[Source — Long Call Calendar Spread (Call Horizontal)]]"
related:
  - "[[Long Put Calendar Spread]]"
  - "[[Diagonal Call Spread]]"
---

# Long Call Calendar Spread

Benefit if the near-term call decays while retaining a longer-dated call; often used with a near-term neutral/bearish and longer-term bullish view.

- Underlying: equity option
- Knowledge id: `strategy.long_call_calendar`
- Review status: `published`
- Futu category: 日历策略 / Calendar Spread

## Legs

- short near-term call (call option)
- long longer-dated call, typically same strike (call option)

## Meaning

Benefit if the near-term call decays while retaining a longer-dated call; often used with a near-term neutral/bearish and longer-term bullish view.

## Scenario

Near-term steady or soft, longer-term still constructive; changes in implied volatility matter.

For traders comfortable managing the front-month expiration and the remaining long call afterward.

## Method

- Maximum profit: At the expiration of the near-term option, the maximum gain would occur should the underlying stock be at the strike price of the expiring option. If the stock were any higher, the expiring option would have intrinsic value, and if the stock were any lower, the longer-term option would have less value.
- Maximum loss: The maximum loss would occur should the two options reach parity. This could happen if the underlying stock declined enough that both options became worthless, or if the stock rose enough that both options went deep in-the-money and traded at their intrinsic value.
- Break-even: Since the options differ in their time to expiration, the level where the strategy breaks even is a function of the underlying stock price, implied volatility and rates of time decay. Should the near-term option expire worthless, breakeven at the longer-term option's expiration would occur if the stock were above the s
- Assignment / expiration: Yes. Early assignment, while possible at any time, generally occurs for a call only when the stock goes ex-dividend. Slight. Should the near-term call (the short side of the spread) be exercised when it expires, the longer-term call option would remain to provide a hedge.

## How the price reacts to volatility and time

- Volatility: An increase in implied volatility, all other things equal, would have an extremely positive impact on this strategy. In general, longer-term options have a greater sensitivity to changes in market volatility, i.e., a higher Vega.
- Time decay: The passage of time, all other things equal, would have a positive impact on this strategy in the beginning. That changes, however, once the near-term option has expired and the strategy becomes simply a long call whose value will be eroded by the passage of time.

## Evidence

### Definition

- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Long Call Calendar Spread (Call Horizontal)` · lines 1–4
  > This strategy combines a longer-term bullish outlook with a near-term neutral/bearish outlook.
- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Description` · lines 5–8
  > Short one call option and long a second call option with a more distant expiration is an example of a long call calendar spread. The strategy most commonly involves calls with the same strike (horizontal spread), but can also be done with different strikes (diagonal spread).
- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Summary` · lines 13–20
  > This strategy combines a longer-term bullish outlook with a near-term neutral/bearish outlook. If the underlying stock remains steady or declines during the life of the near-term option, that option will expire worthless and leave the investor owning the longer-term option free and clear. If both options have the same

### Legs

- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Example` · lines 21–33
  > - Short 1 XYZ near 60 call - Long 1 XYZ far 60 call MAXIMUM GAIN - Unlimited MAXIMUM LOSS - Net premium paid

### Objective

- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Description` · lines 5–8
  > Short one call option and long a second call option with a more distant expiration is an example of a long call calendar spread. The strategy most commonly involves calls with the same strike (horizontal spread), but can also be done with different strikes (diagonal spread).
- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Motivation` · lines 34–37
  > The investor hopes to reduce the cost of purchasing a longer-term call option.

### Market Outlook

- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Outlook` · lines 9–12
  > Looking for either a steady to slightly declining stock price during the life of the near-term option and then a move higher during the life of the far-term option, or a sharp move upward in implied volatility.

### Max Gain

- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Example` · lines 21–33
  > - Short 1 XYZ near 60 call - Long 1 XYZ far 60 call MAXIMUM GAIN - Unlimited MAXIMUM LOSS - Net premium paid
- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Max Gain` · lines 46–49
  > At the expiration of the near-term option, the maximum gain would occur should the underlying stock be at the strike price of the expiring option. If the stock were any higher, the expiring option would have intrinsic value, and if the stock were any lower, the longer-term option would have less value. Once the near-te

### Max Loss

- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Example` · lines 21–33
  > - Short 1 XYZ near 60 call - Long 1 XYZ far 60 call MAXIMUM GAIN - Unlimited MAXIMUM LOSS - Net premium paid
- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Max Loss` · lines 42–45
  > The maximum loss would occur should the two options reach parity. This could happen if the underlying stock declined enough that both options became worthless, or if the stock rose enough that both options went deep in-the-money and traded at their intrinsic value. In either case, the loss would be the premium paid to

### Breakeven

- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Breakeven` · lines 54–57
  > Since the options differ in their time to expiration, the level where the strategy breaks even is a function of the underlying stock price, implied volatility and rates of time decay. Should the near-term option expire worthless, breakeven at the longer-term option's expiration would occur if the stock were above the s

### Volatility Effect

- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Volatility` · lines 58–61
  > An increase in implied volatility, all other things equal, would have an extremely positive impact on this strategy. In general, longer-term options have a greater sensitivity to changes in market volatility, i.e., a higher Vega. Be aware, that the near-term and far-term options could and probably will trade at differe

### Time Decay Effect

- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Time Decay` · lines 62–65
  > The passage of time, all other things equal, would have a positive impact on this strategy in the beginning. That changes, however, once the near-term option has expired and the strategy becomes simply a long call whose value will be eroded by the passage of time. In general, an option's rate of time decay increases as

### Assignment Or Expiration Risk

- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Assignment Risk` · lines 66–71
  > Yes. Early assignment, while possible at any time, generally occurs for a call only when the stock goes ex-dividend. Should early exercise occur, using the the longer-term option to cover the assignment would require establishing a short stock position for one business day. And be aware, a situation where a stock is in
- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Expiration Risk` · lines 72–75
  > Slight. Should the near-term call (the short side of the spread) be exercised when it expires, the longer-term call option would remain to provide a hedge. If the longer-term option were held into expiration, it may be exercised on the investor's behalf by their brokerage firm if it's in-the-money.

### Suitability Constraints

- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Motivation` · lines 34–37
  > The investor hopes to reduce the cost of purchasing a longer-term call option.
- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Comments` · lines 76–81
  > The difference in time to expiration of these two call options results in their having a different Theta, Delta and Gamma. Obviously, the near-term call suffers more from time decay, i.e., has a greater Theta. Less intuitively, the near-term call has a lower Delta but a higher Gamma (if the strike is at-the-money). Thi

## See also

- related to: [[Long Put Calendar Spread]]
- related to: [[Diagonal Call Spread]]

See the [[index|Wiki Index]].
