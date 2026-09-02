---
type: concept
title: Theta and time decay
status: evergreen
created: 2026-09-02
updated: 2026-09-02
tags:
  - concept
  - greek
domain: options
aliases:
  - theta
  - time decay
sources:
  - "[[Source — Theta]]"
related:
  - "[[Covered Call (Buy-Write)]]"
---

# Theta and time decay

Theta estimates daily option-premium decay with other factors unchanged. Time decay is not linear and tends to accelerate as expiration approaches.

## Terms

- theta
- time decay
- time value
- expiration
- implied volatility

## Content

Both long and short option holders should be aware of the effects of Theta on an option premium. Theta is represented in an actual dollar or premium amount. Theta represents, in theory, how much an option’s premium may decay per day with all other pricing factors remaining the same.
Theta or time decay is not linear. The theoretical rate of decay will tend to increase as time to expiration decreases. Thus, the amount of decay indicated by Theta tends to be gradual at first and accelerates as expiration approaches. Upon expiration, an option has no time value and is worth its intrinsic value only.. Pricing models take into account weekends, so options will tend to decay seven days over the course of five trading days. However, there is no industry-wide method for decaying options so different models show the impact of time decay differently. If a pricing model is decaying options too quickly, current markets may look too high when compared to the model’s theoretical values, and if the model is displaying the decay as too slowly, the current markets may look too cheap compared to your model’s theoretical values.
If stock was trading for $50 and a $50 strike call as trading at $3 with a Theta of .05, an investor would anticipate that option to lose about $.05 per day, all things being equal. If a day passed without a change in the option price, then one of the other variables must have changed. In most cases, it would likely have been an increase in implied volatility. If the option decreased more than $.05 an investor might deduce that implied volatility on that strike or product might have dropped as well. And as expiration approaches, it is likely Theta would become increasingly negative.
Here is an example of how Theta tends to behave over time. A constant 40% implied volatility is being used on a 50 strike call option with OICX equal to $50. This example, which was derived using OIC pricing calculators, assumes an interest rate of 2% and no changes to implied volatility or the underlying price during the life of the option.
Note how quickly time premium begins to decay around 30 days prior to expiration. We can see that Theta is not a linear progression as the option advances toward expiration. Rather, options with the least remaining time until expiration will tend to decay the most. The at-the-money call is the most vulnerable to a lack of movement in the underlying.
The implied volatility of a product will determine the amount of time premium, and in turn affect Theta amounts. In general, the higher the implied volatility levels, the higher the Theta amount. This does not mean that investors can sell options in high implied volatility stocks and expect to earn time decay right away. Many times, options trade at elevated implied volatility levels because of the actual historical volatility or because of an earnings announcement, product announcement, etc. Here is a chart that looks at general Theta amounts for different implied volatilities:
At-the-money options will have the most exposure to time decay. And, as the chart shows, options that are either deep-in-the-money or far out-of-the-money will have very little decay as they have less time premium. Also, because of the fact that calls have unlimited upside and that option premiums represent a hedged value (some institutional investors and market makers receive a credit for hedging their long calls with short stock, driving the call prices slightly higher) call prices will tend to trade slightly over put premiums.

## Evidence

- [[Source — Theta]] · `Theta` · lines 1–21
  > Both long and short option holders should be aware of the effects of Theta on an option premium. Theta is represented in an actual dollar or premium amount. Theta represents, in theory, how much an option’s premium may decay per day with all other pricing factors remaining the same. Theta or time decay is not linear. T

## See also

- affects (inbound): [[Covered Call (Buy-Write)]]

See the [[index|Wiki Index]].
