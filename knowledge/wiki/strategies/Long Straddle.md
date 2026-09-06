---
type: entity
title: Long Straddle
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - entity
  - strategy
  - straddle
entity_type: option-strategy
aliases:
  - long straddle
  - straddle
sources:
  - "[[Source — Long Straddle]]"
  - "[[Source — Optionistics Chapter 5 Straddles]]"
related:
  - "[[Strap]]"
  - "[[Strip]]"
  - "[[Long Strangle (Long Combination)]]"
---

# Long Straddle

Profit from a large move in either direction or a sharp rise in implied volatility. Optionistics: equal number of puts and calls on the same stock at the same strike. Profit-and-loss numbers stay with the Options Industry Council.

- Underlying: equity option
- Knowledge id: `strategy.long_straddle`
- Review status: `published`
- Futu category: 跨式策略 / Straddle

## Legs

- long at-the-money call (strike near the current stock price)
- long at-the-money put, same strike and expiration

## Meaning

Profit from a large move in either direction or a sharp rise in implied volatility.

## Scenario

Expects a big move up or down; harmed by quiet markets and time decay.

For investors who can afford two premiums and need a sufficiently large move before expiration.

## Method

- Maximum profit: The maximum gain is unlimited. The best that can happen is for the stock to make a big move in either direction.
- Maximum loss: The maximum loss is limited to the two premiums paid. The worst that can happen is for the stock price to hold steady and implied volatility to decline.
- Break-even: This strategy breaks even if, at expiration, the stock price is either above or below the strike price by the amount of premium paid. At either of those levels, one option's intrinsic value will equal the premium paid for both options while the other option will be expiring worthless.
- Assignment / expiration: None. The investor is in control. Slight. If the options are held into expiration, one of them may be subject to automatic exercise.

## How the price reacts to volatility and time

- Volatility: Extremely important. This strategy's success would be fueled by an increase in implied volatility.
- Time decay: Extremely important, negative effect. Because this strategy consists of being long a call and a put, both of them at-the-money at least at the beginning, every day that passes without a move in the stock's price will cause the total premium of this position to suffer a significant erosion of value.

## Evidence

### Definition

- [[Source — Long Straddle]] · `Long Straddle` · lines 1–4
  > This strategy consists of buying a call option and a put option with the same strike price and expiration.
- [[Source — Long Straddle]] · `Description` · lines 5–10
  > A long straddle is a combination of buying a call and buying a put, both with the same strike price and expiration. Together, they produce a position that should profit if the stock makes a big move either up or down. Typically, investors buy the straddle because they predict a big price move and/or a great deal of vol
- [[Source — Long Straddle]] · `Summary` · lines 15–22
  > This strategy consists of buying a call option and a put option with the same strike price and expiration. The combination generally profits if the stock price moves sharply in either direction during the life of the options. ; Max loss at 60, profit increases as price moves away from 60 in either direction") Net Posit
- [[Source — Optionistics Chapter 5 Straddles]] · `Straddles`
  > A straddle consists of an equal number of puts and calls on the same stock at the same strike. The objective of a long straddle is to profit from a large swing in the price of the underlying stock.

### Legs

- [[Source — Long Straddle]] · `Example` · lines 23–35
  > - Long 1 XYZ 60 call - Long 1 XYZ 60 put MAXIMUM GAIN - Unlimited MAXIMUM LOSS - Premiums paid

### Objective

- [[Source — Long Straddle]] · `Description` · lines 5–10
  > A long straddle is a combination of buying a call and buying a put, both with the same strike price and expiration. Together, they produce a position that should profit if the stock makes a big move either up or down. Typically, investors buy the straddle because they predict a big price move and/or a great deal of vol
- [[Source — Long Straddle]] · `Motivation` · lines 36–39
  > The long straddle is a way to profit from increased volatility or a sharp move in the underlying stock's price.

### Market Outlook

- [[Source — Long Straddle]] · `Outlook` · lines 11–14
  > Looking for a sharp move in the stock price, in either direction, during the life of the options. Because of the effect of two premium outlays on the breakeven, the investor's opinion is fairly strongly held and time-specific.

### Max Gain

- [[Source — Long Straddle]] · `Example` · lines 23–35
  > - Long 1 XYZ 60 call - Long 1 XYZ 60 put MAXIMUM GAIN - Unlimited MAXIMUM LOSS - Premiums paid
- [[Source — Long Straddle]] · `Max Gain` · lines 48–51
  > The maximum gain is unlimited. The best that can happen is for the stock to make a big move in either direction. The profit at expiration will be the difference between the stock's price and the strike price, less the premium paid for both options. There is no limit to profit potential on the upside, and the downside p

### Max Loss

- [[Source — Long Straddle]] · `Example` · lines 23–35
  > - Long 1 XYZ 60 call - Long 1 XYZ 60 put MAXIMUM GAIN - Unlimited MAXIMUM LOSS - Premiums paid
- [[Source — Long Straddle]] · `Max Loss` · lines 44–47
  > The maximum loss is limited to the two premiums paid. The worst that can happen is for the stock price to hold steady and implied volatility to decline. If at expiration the stock's price is exactly at-the-money, both options will expire worthless, and the entire premium paid to put on the position will be lost.

### Breakeven

- [[Source — Long Straddle]] · `Breakeven` · lines 58–65
  > This strategy breaks even if, at expiration, the stock price is either above or below the strike price by the amount of premium paid. At either of those levels, one option's intrinsic value will equal the premium paid for both options while the other option will be expiring worthless. Upside breakeven = strike + premiu

### Volatility Effect

- [[Source — Long Straddle]] · `Volatility` · lines 66–71
  > Extremely important. This strategy's success would be fueled by an increase in implied volatility. Even if the stock held steady, if there were a quick rise in implied volatility, the value of both options would tend to rise. Conceivably that could allow the investor to close out the straddle for a profit well before e

### Time Decay Effect

- [[Source — Long Straddle]] · `Time Decay` · lines 72–75
  > Extremely important, negative effect. Because this strategy consists of being long a call and a put, both of them at-the-money at least at the beginning, every day that passes without a move in the stock's price will cause the total premium of this position to suffer a significant erosion of value. What's more, the rat

### Assignment Or Expiration Risk

- [[Source — Long Straddle]] · `Assignment Risk` · lines 76–79
  > None. The investor is in control.
- [[Source — Long Straddle]] · `Expiration Risk` · lines 80–83
  > Slight. If the options are held into expiration, one of them may be subject to automatic exercise. The investor should be aware of the rules regarding exercise, so that exercise happens if, and only if, the option's intrinsic value exceeds an acceptable minimum.

### Suitability Constraints

- [[Source — Long Straddle]] · `Motivation` · lines 36–39
  > The long straddle is a way to profit from increased volatility or a sharp move in the underlying stock's price.
- [[Source — Long Straddle]] · `Comments` · lines 84–87
  > This strategy could be seen as a race between time decay and volatility. The passage of time erodes the position's value a little bit every day, often at an accelerating rate. The hoped-for volatility increase might come at any moment or might never occur at all.

## See also

- related to: [[Strap]]
- related to: [[Strip]]
- related to: [[Long Strangle (Long Combination)]]

See the [[index|Wiki Index]].
