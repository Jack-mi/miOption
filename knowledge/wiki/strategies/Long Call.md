---
type: entity
title: Long Call
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - entity
  - strategy
  - single-option
entity_type: option-strategy
aliases:
  - long call
  - buy call
sources:
  - "[[Source — Long Call]]"
related: []
---

# Long Call

Participate in an expected rise in the underlying with limited risk equal to the premium paid.

- Underlying: equity option
- Knowledge id: `strategy.long_call`
- Review status: `published`
- Futu category: 单腿期权 / Single Option

## Legs

- long one or more calls (call option)

## Meaning

Participate in an expected rise in the underlying with limited risk equal to the premium paid.

## Scenario

Bullish; wants a timely rally and/or rising implied volatility before expiration.

For bullish investors who accept that the call can expire worthless and that timing before expiration is critical.

## Method

- Maximum profit: The profit potential is theoretically unlimited. The best that can happen is for the stock price to rise to infinity.
- Maximum loss: The maximum loss is limited and occurs if the investor still holds the call at expiration and the stock is below the strike price. The option would expire worthless, and the loss would be the price paid for the call option.
- Break-even: At expiration, the strategy breaks even if the stock price is equal to the strike price plus the initial cost of the call option. Any stock price above that point produces a net profit.
- Assignment / expiration: None. The investor is in control. Slight. If the option expires in-the-money it may be exercised for you by your brokerage firm.

## How the price reacts to volatility and time

- Volatility: An increase in implied volatility would have a positive impact on this strategy, all other things being equal. Volatility tends to boost the value of any long option strategy, because it indicates a greater mathematical probability that the stock will move enough to give the option intrinsic value (or add to its curren
- Time decay: As with most long option strategies, the passage of time has a negative impact here, all other things being equal. As time remaining to expiration disappears, the statistical chances of achieving further gains in intrinsic value shrink.

## Evidence

### Definition

- [[Source — Long Call]] · `Long Call` · lines 1–4
  > This strategy profits if the underlying stock is at the body of the butterfly at expiration.
- [[Source — Long Call]] · `Description` · lines 5–16
  > A long call strategy typically doesn't appreciate in a 1-to-1 ratio with the stock, but pricing models often give us a reasonable estimate about how a $1 stock price change might affect the call's value, assuming other factors remain the same. What's more, the percentage gains relative to the premium can be significant
- [[Source — Long Call]] · `Summary` · lines 37–40
  > This strategy consists of buying a call option. Buying a call is for investors who want a chance to participate in the underlying stock's expected appreciation during the term of the option. If things go as planned, the investor will be able to sell the call at a profit at some point before expiration.

### Legs

- [[Source — Long Call]] · `Example` · lines 17–30
  > - Long 1 XYZ 60 call MAXIMUM GAIN - Unlimited MAXIMUM LOSS - Premium paid On the other hand, if a quick turnaround starts looking unlikely, it might make sense to sell the call while it still has some time value. A timely decision might allow the investor to recoup some or even all of the investment.

### Objective

- [[Source — Long Call]] · `Description` · lines 5–16
  > A long call strategy typically doesn't appreciate in a 1-to-1 ratio with the stock, but pricing models often give us a reasonable estimate about how a $1 stock price change might affect the call's value, assuming other factors remain the same. What's more, the percentage gains relative to the premium can be significant
- [[Source — Long Call]] · `Motivation` · lines 41–44
  > The investor buys calls as a way to profit from growth in the underlying stock's price, without the risk and up-front capital outlay of outright stock ownership. The smaller initial outlay also gives the buyer a chance to achieve greater percentage gains (i.e., greater leverage).

### Market Outlook

- [[Source — Long Call]] · `Outlook` · lines 31–36
  > A call buyer is definitely bullish in the near term, anticipating gains in the underlying stock during the life of the option. An investor's long-term outlook could range from very bullish to somewhat bullish or even neutral. If the long-term outlook is solidly bearish, another strategy alternative might be more approp

### Max Gain

- [[Source — Long Call]] · `Example` · lines 17–30
  > - Long 1 XYZ 60 call MAXIMUM GAIN - Unlimited MAXIMUM LOSS - Premium paid On the other hand, if a quick turnaround starts looking unlikely, it might make sense to sell the call while it still has some time value. A timely decision might allow the investor to recoup some or even all of the investment.
- [[Source — Long Call]] · `Max Gain` · lines 55–58
  > The profit potential is theoretically unlimited. The best that can happen is for the stock price to rise to infinity. In that case, the investor could either sell the option at a virtually infinite profit, or exercise it and purchase stock at the strike price and sell it for 'infinity'.

### Max Loss

- [[Source — Long Call]] · `Example` · lines 17–30
  > - Long 1 XYZ 60 call MAXIMUM GAIN - Unlimited MAXIMUM LOSS - Premium paid On the other hand, if a quick turnaround starts looking unlikely, it might make sense to sell the call while it still has some time value. A timely decision might allow the investor to recoup some or even all of the investment.
- [[Source — Long Call]] · `Max Loss` · lines 51–54
  > The maximum loss is limited and occurs if the investor still holds the call at expiration and the stock is below the strike price. The option would expire worthless, and the loss would be the price paid for the call option.

### Breakeven

- [[Source — Long Call]] · `Breakeven` · lines 69–74
  > At expiration, the strategy breaks even if the stock price is equal to the strike price plus the initial cost of the call option. Any stock price above that point produces a net profit. In other words: Breakeven = strike + premium

### Volatility Effect

- [[Source — Long Call]] · `Volatility` · lines 75–80
  > An increase in implied volatility would have a positive impact on this strategy, all other things being equal. Volatility tends to boost the value of any long option strategy, because it indicates a greater mathematical probability that the stock will move enough to give the option intrinsic value (or add to its curren

### Time Decay Effect

- [[Source — Long Call]] · `Time Decay` · lines 81–86
  > As with most long option strategies, the passage of time has a negative impact here, all other things being equal. As time remaining to expiration disappears, the statistical chances of achieving further gains in intrinsic value shrink. Furthermore, the cost-to-carry savings offered by a long call strategy, versus an o

### Assignment Or Expiration Risk

- [[Source — Long Call]] · `Assignment Risk` · lines 87–90
  > None. The investor is in control.
- [[Source — Long Call]] · `Expiration Risk` · lines 91–96
  > Slight. If the option expires in-the-money it may be exercised for you by your brokerage firm. Since this investor did not originally set aside the cash to buy the stock, an unexpected exercise could be a major inconvenience and require urgent measures to come up with the cash for settlement. Every investor carrying a

### Suitability Constraints

- [[Source — Long Call]] · `Motivation` · lines 41–44
  > The investor buys calls as a way to profit from growth in the underlying stock's price, without the risk and up-front capital outlay of outright stock ownership. The smaller initial outlay also gives the buyer a chance to achieve greater percentage gains (i.e., greater leverage).
- [[Source — Long Call]] · `Comments` · lines 97–104
  > All option investors have reason to monitor the underlying stock and keep track of dividends. This applies to long call holders too, regardless of whether they intend to acquire the stock. On an ex-dividend date, the amount of the dividend is deducted from the value of the underlying stock. That in turn puts downward p


See the [[index|Wiki Index]].
