---
type: concept
title: Option premium and pricing drivers
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - concept
  - pricing
domain: options
aliases:
  - options pricing
  - intrinsic value
  - time value
sources:
  - "[[Source — Options Pricing]]"
  - "[[Source — Optionistics Chapter 3 Option Pricing]]"
  - "[[Source — Optionistics Chapter 3 Underlying Price vs Strike]]"
  - "[[Source — Optionistics Chapter 3 Volatility]]"
  - "[[Source — Optionistics Chapter 3 Dividends]]"
related: []
---

# Option premium and pricing drivers

An option premium is composed of intrinsic value and time value. Underlying price, strike, time to expiration, implied volatility, dividends, and interest rates affect the premium.

## Terms

- premium
- intrinsic value
- time value
- implied volatility
- strike
- expiration

## Content

An option’s premium has two main components: intrinsic value and time value.

A call option is in-the-money when the underlying security's price is higher than the strike price.

A put option is in-the-money if the underlying security's price is less than the strike price. Only in-the-money options have intrinsic value. It represents the difference between the current price of the underlying security and the option's exercise price, or strike price.

Time value is any premium in excess of intrinsic value before expiration. Time value is often explained as the amount an investor is willing to pay for an option above its intrinsic value. This amount reflects hope that the option’s value increases before expiration due to a favorable change in the underlying security’s price. The longer the amount of time available for market conditions to work to an investor's benefit, the greater the time value.

Factors having a significant effect on options premium include:
- Underlying price
- Strike
- Time until expiration
- Implied volatility
- Dividends
- Interest rate
Dividends and risk-free interest rate have a lesser effect.
Changes in the underlying security price can increase or decrease the value of an option. These price changes have opposite effects on calls and puts. For instance, as the value of the underlying security rises, a call will generally increase. However, the value of a put will generally decrease in price. A decrease in the underlying security's value generally has the opposite effect.
The strike price determines whether an option has intrinsic value. An option's premium (intrinsic value plus time value) generally increases as the option becomes further in-the-money. It decreases as the option becomes more deeply out-of-the-money.
Time until expiration, as discussed above, affects the time value component of an option's premium. Generally, as expiration approaches, the levels of an option's time value decrease or erode for both puts and calls. This effect is most noticeable with at-the-money options.
The effect of implied volatility is subjective and difficult to quantify. It can significantly affect the time value portion of an option's premium. Volatility is a measure of risk (uncertainty), or variability of price of an option's underlying security. Higher volatility estimates indicate greater expected fluctuations (in either direction) in underlying price levels. This expectation generally results in higher option premiums for puts and calls alike. It is most noticeable with at-the-money options.
The effect of an underlying security's dividends and the current risk-free interest rate has a small but measurable effect on option premiums. This effect reflects the cost to carry shares in an underlying security. Cost of carry is the potential interest paid for margin or received from alternative investments (such as a Treasury bill) and the dividends from owning shares outright. Pricing takes into account an option’s hedged value so dividends from stock and interest paid or received for stock positions used to hedge options are a factor.
Please visit our learning resources by topic pages to learn more about Options Pricing.

Optionistics (secondary): the three largest drivers are underlying versus strike, time to expiration, and volatility. Models also take the risk-free rate and dividend yield. An option is worth at least its intrinsic value except in unusual cases. Higher volatility raises both call and put prices. A dividend tends to discount the call and premium the put.

## Evidence

- [[Source — Options Pricing]] · `Options Pricing` · lines 1–4
  > An option’s premium has two main components: intrinsic value and time value.
- [[Source — Options Pricing]] · `Intrinsic Value (Calls)` · lines 5–10
  > A call option is in-the-money when the underlying security's price is higher than the strike price.
- [[Source — Options Pricing]] · `Intrinsic Value (Puts)` · lines 11–14
  > A put option is in-the-money if the underlying security's price is less than the strike price. Only in-the-money options have intrinsic value. It represents the difference between the current price of the underlying security and the option's exercise price, or strike price.
- [[Source — Options Pricing]] · `Time Value` · lines 15–18
  > Time value is any premium in excess of intrinsic value before expiration. Time value is often explained as the amount an investor is willing to pay for an option above its intrinsic value. This amount reflects hope that the option’s value increases before expiration due to a favorable change in the underlying security’
- [[Source — Options Pricing]] · `Major Factors Influencing Options Premium` · lines 19–42
  > Factors having a significant effect on options premium include: - Underlying price - Strike - Time until expiration - Implied volatility - Dividends - Interest rate Dividends and risk-free interest rate have a lesser effect. Changes in the underlying security price can increase or decrease the value of an option. These
- [[Source — Optionistics Chapter 3 Option Pricing]] · `Option Pricing`
  > The three factors which have the greatest impact on the option price are 1) the price of the underlying stock versus the strike price, 2) the time until expiration, and 3) the volatility. Most option pricing models consider five basic factors when computing option prices: price of the underlying security vs. the strike price, term, volatility, prevailing risk free interest rate, the dividend yield of the underlying stock.
- [[Source — Optionistics Chapter 3 Underlying Price vs Strike]] · `Underlying Price vs Strike`
  > An option is worth at least as much as it is in the money. Except in some unusual cases, options will be worth at least as much as they are in the money.
- [[Source — Optionistics Chapter 3 Volatility]] · `Volatility`
  > The volatility is a measure of how likely it is that the underlying stock price will change. This is typically computed by taking the standard deviation of price changes over time. The price of both the call and the put increase as the volatility increases.
- [[Source — Optionistics Chapter 3 Dividends]] · `Dividends`
  > If the underlying stock pays a dividend, the CALL will sell at a discount and the PUT will sell at a premium. When a stock dividend is paid, the price of the stock is reduced by the amount of the dividend payout.


See the [[index|Wiki Index]].
