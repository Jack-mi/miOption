---
type: entity
title: Long Put
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - entity
  - strategy
  - single-option
entity_type: option-strategy
aliases:
  - long put
  - buy put
sources:
  - "[[Source — Long Put]]"
related: []
---

# Long Put

Profit from an expected decline in the underlying with risk limited to the premium paid.

- Underlying: equity option
- Knowledge id: `strategy.long_put`
- Review status: `published`
- Futu category: 单腿期权 / Single Option

## Legs

- long one or more puts (put option)

## Meaning

Profit from an expected decline in the underlying with risk limited to the premium paid.

## Scenario

Bearish; wants a timely drop and/or rising implied volatility before expiration.

For bearish investors who prefer defined risk instead of shorting stock; must realize gains before expiration.

## Method

- Maximum profit: The profit potential is limited but substantial. The best that can happen is for the stock to become worthless.
- Maximum loss: The maximum loss is limited. The worst that can happen is for the stock price to be above the strike price at expiration with the put owner still holding the position.
- Break-even: At expiration, the strategy breaks even if the stock price equals the strike price minus the cost of the option. Any stock price below that level produces a net profit.
- Assignment / expiration: None. The investor is in control. Slight. If the option is in-the-money at expiration, it may be exercised on your behalf by your brokerage firm.

## How the price reacts to volatility and time

- Volatility: An increase in implied volatility would have a positive impact on this strategy, all other things being equal. Volatility tends to boost the value of any long option strategy, because it indicates a greater mathematical probability that the stock will move enough to give the option intrinsic value (or add to its curren
- Time decay: As with most long option strategies, the passage of time has a negative impact, all other things being equal. As time remaining until expiration disappears, the statistical chances of achieving further gains shrink.

## Evidence

### Definition

- [[Source — Long Put]] · `Long Put` · lines 1–4
  > This strategy consists of buying puts as a means to profit if the stock price moves lower.
- [[Source — Long Put]] · `Description` · lines 5–16
  > The investor buys a put contract that is compatible with the expected timing and size of a downturn. Although a put usually doesn’t appreciate $1 for every $1 that the stock declines, the percentage gains can be significant. Exercising a put would result in the sale of the underlying stock. These comments focus on long
- [[Source — Long Put]] · `Summary` · lines 37–42
  > This strategy consists of buying puts as a means to profit if the stock price moves lower. It is a candidate for bearish investors who want to participate in an anticipated downturn, but without the risk and inconveniences of selling the stock short. The time horizon is limited to the life of the option.

### Legs

- [[Source — Long Put]] · `Example` · lines 17–30
  > - Long 1 XYZ 60 put MAXIMUM GAIN - Strike price - premium paid MAXIMUM LOSS - Premium paid If the put holder is willing to forfeit 100% of the premium paid and is convinced a decline is imminent, one choice is to wait until the last trading day. If the stock falls, the put might generate a nice profit after all. Howeve

### Objective

- [[Source — Long Put]] · `Description` · lines 5–16
  > The investor buys a put contract that is compatible with the expected timing and size of a downturn. Although a put usually doesn’t appreciate $1 for every $1 that the stock declines, the percentage gains can be significant. Exercising a put would result in the sale of the underlying stock. These comments focus on long
- [[Source — Long Put]] · `Motivation` · lines 43–48
  > A put buyer has the opportunity to profit from a fall in the stock's price, without risking an unlimited amount of capital, as a short stock seller does. What's more, the leverage involved in a long put strategy can generate attractive percentage returns if the forecast is right. Another common use for puts is hedging

### Market Outlook

- [[Source — Long Put]] · `Outlook` · lines 31–36
  > The investor is looking for a sharp decline in the stock's price during the life of the option. This strategy is compatible with a variety of long-term forecasts for the underlying stock, from very bearish to neutral. However, if the investor is firmly bullish on the underlying stock in the long run, other strategy alt

### Max Gain

- [[Source — Long Put]] · `Example` · lines 17–30
  > - Long 1 XYZ 60 put MAXIMUM GAIN - Strike price - premium paid MAXIMUM LOSS - Premium paid If the put holder is willing to forfeit 100% of the premium paid and is convinced a decline is imminent, one choice is to wait until the last trading day. If the stock falls, the put might generate a nice profit after all. Howeve
- [[Source — Long Put]] · `Max Gain` · lines 57–60
  > The profit potential is limited but substantial. The best that can happen is for the stock to become worthless. In that case, the investor can theoretically do one of two things: sell the put for its intrinsic value or exercise the put to sell the underlying stock at the strike price and simultaneously buy the equivale

### Max Loss

- [[Source — Long Put]] · `Example` · lines 17–30
  > - Long 1 XYZ 60 put MAXIMUM GAIN - Strike price - premium paid MAXIMUM LOSS - Premium paid If the put holder is willing to forfeit 100% of the premium paid and is convinced a decline is imminent, one choice is to wait until the last trading day. If the stock falls, the put might generate a nice profit after all. Howeve
- [[Source — Long Put]] · `Max Loss` · lines 53–56
  > The maximum loss is limited. The worst that can happen is for the stock price to be above the strike price at expiration with the put owner still holding the position. The put option expires worthless and the loss is the price paid for the put.

### Breakeven

- [[Source — Long Put]] · `Breakeven` · lines 71–76
  > At expiration, the strategy breaks even if the stock price equals the strike price minus the cost of the option. Any stock price below that level produces a net profit. In other words: Breakeven = strike – premium

### Volatility Effect

- [[Source — Long Put]] · `Volatility` · lines 77–82
  > An increase in implied volatility would have a positive impact on this strategy, all other things being equal. Volatility tends to boost the value of any long option strategy, because it indicates a greater mathematical probability that the stock will move enough to give the option intrinsic value (or add to its curren

### Time Decay Effect

- [[Source — Long Put]] · `Time Decay` · lines 83–88
  > As with most long option strategies, the passage of time has a negative impact, all other things being equal. As time remaining until expiration disappears, the statistical chances of achieving further gains shrink. That tends to be reflected in eroding time premiums, which put downward pressure on the put's market val

### Assignment Or Expiration Risk

- [[Source — Long Put]] · `Assignment Risk` · lines 89–92
  > None. The investor is in control.
- [[Source — Long Put]] · `Expiration Risk` · lines 93–98
  > Slight. If the option is in-the-money at expiration, it may be exercised on your behalf by your brokerage firm. Since this investor did not own the underlying stock, an unexpected exercise could require urgent measures to find the stock for delivery at settlement. A short stock position might be a problematic outcome f

### Suitability Constraints

- [[Source — Long Put]] · `Motivation` · lines 43–48
  > A put buyer has the opportunity to profit from a fall in the stock's price, without risking an unlimited amount of capital, as a short stock seller does. What's more, the leverage involved in a long put strategy can generate attractive percentage returns if the forecast is right. Another common use for puts is hedging
- [[Source — Long Put]] · `Comments` · lines 99–104
  > All option investors have reason to monitor the underlying stock and keep track of dividends. This applies to long put investors, too. On an ex-dividend date, the amount of the dividend is deducted from the value of the underlying stock. Assuming nothing else has changed, a lower stock value typically boosts the put op


See the [[index|Wiki Index]].
