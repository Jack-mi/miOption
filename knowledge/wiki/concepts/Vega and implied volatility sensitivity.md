---
type: concept
title: Vega and implied volatility sensitivity
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - concept
  - greek
domain: options
aliases:
  - vega
  - implied volatility sensitivity
sources:
  - "[[Source — Vega]]"
  - "[[Source — Optionistics Chapter 2 More Definitions]]"
  - "[[Source — Optionistics Chapter 4 Significance of Volatility]]"
related:
  - "[[Covered Call (Buy-Write)]]"
---

# Vega and implied volatility sensitivity

Vega measures the option premium's sensitivity to a one-percentage-point change in implied volatility. Longer-dated options generally have higher Vega than near-term options.

## Terms

- vega
- implied volatility
- option premium
- term

## Content

Vega measures an option’s sensitivity to changes in implied volatility. Implied volatility is measured in percentage terms and is a key variable in pricing models. Implied volatility has no direct correlation to actual past historical or statistical volatility; rather it is a measure of predicted future movement. Implied volatility tends to increase when there is uncertainty or anticipated news, while it tends to decrease in times of calm. Some investors use a stock’s historical volatility as an indication of where the implied volatility should be, but the market is the ultimate determining factor of current implied volatility levels. Also, Vega and implied volatility can change without any movement in the underlying.
If we know what the current market premiums are for the calls and the puts on a certain strike, we can solve for the implied volatility using the OIC Calculators. The calculators provide the price-sensitivity measures, including Vega. If a large sell order came into the market and the price of the option declined due to lack of interested buyers at the current price, we would see a decline in the implied volatility if there were no change in the other assumptions. Increased demand and higher premiums mean an increase in implied volatility. Changes in implied volatility can also impact the other sensitivity measures, such as Delta and Gamma so traders should be aware how these sensitivity measures work together.
Vega measures the amount of increase or decrease in premium based on a 1% (100 basis points) change in the implied volatility assumption. Longer-term options tend to have higher Vega than near-term options. Longer-termed options are typically more expensive, and a 1% change in implied volatility will represent a larger dollar amount of that premium than an option with a lower premium. If OICX were trading $50 and front-month $50 call was trading $2 and the 12-month-out $50 call was trading $5, the more expensive call would be more profoundly affected by a 1% change in implied volatility. To increase in price by identical amounts, the near term option’s implied volatility would have to have gone up around 2.5x that of the longer-termed option.
For example, OICX is trading at $50, a call with 12 months until expiration has an implied volatility of 30%, a Vega of .15, and a current market value of $4. If implied volatility were to instantly rise 2% to 32%, the investor might expect the option premium to increase by: .15 X 2 = $.30 to around $4.30, all things being equal. A decrease in implied volatility by 5% may result in the option losing around: .15 X 5 = $.75 in value. As we can see, changes in implied volatility can have drastic effects on an option price, probably second only to underlying price in importance.

Optionistics (secondary): historical volatility is an annualized standard deviation of past price changes; implied volatility is backed out from the current market price given the other model inputs. With strike and expiry fixed, implied volatility is the comparison of relative expense across a chain.

## Evidence

- [[Source — Vega]] · `Vega` · lines 1–9
  > Vega measures an option’s sensitivity to changes in implied volatility. Implied volatility is measured in percentage terms and is a key variable in pricing models. Implied volatility has no direct correlation to actual past historical or statistical volatility; rather it is a measure of predicted future movement. Impli
- [[Source — Optionistics Chapter 2 More Definitions]] · `More Definitions`
  > Historical Volatility - the measure of the likelihood of a stock price to change. This is typically expressed as the annualized standard deviation of price changes in the underlying stock for a period of 3,6 or 12 months. Implied volatility - the volatility which is computed using the current market price, and other known, fixed model inputs.
- [[Source — Optionistics Chapter 4 Significance of Volatility]] · `The Significance Of Volatility`
  > An effective method of computing the relative expense of different options is to compute the implied volatility. The implied volatility is the measure of the likelihood that the underlying stock price will change based on the price of the option.

## See also

- affects (inbound): [[Covered Call (Buy-Write)]]

See the [[index|Wiki Index]].
