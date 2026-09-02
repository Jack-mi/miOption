---
type: entity
title: Long Strangle (Long Combination)
status: evergreen
created: 2026-09-02
updated: 2026-09-02
tags:
  - entity
  - strategy
  - strangle
entity_type: option-strategy
aliases:
  - long strangle
  - strangle
sources:
  - "[[Source — Long Strangle (Long Combination)]]"
related: []
---

# Long Strangle (Long Combination)

Profit from a large move either way at lower cost than a straddle, needing a bigger move to break even.

- Underlying: equity option
- Knowledge id: `strategy.long_strangle`
- Review status: `published`
- Futu category: 宽跨式策略 / Strangle

## Legs

- long OTM call (call option)
- long OTM put, same expiration (put option)

## Meaning

Profit from a large move either way at lower cost than a straddle, needing a bigger move to break even.

## Scenario

Expects a large move; quieter than a straddle but still hurt by time decay if the stock stays between strikes.

For investors seeking cheaper long-volatility exposure who accept a wider breakeven band.

## Method

- Max gain: The maximum gain is unlimited. The maximum gain occurs if the underlying stock goes to infinity, and a very substantial gain would occur if the stock became worthless.
- Max loss: The maximum loss is limited. The maximum loss occurs if the underlying stock remains between the strike prices until expiration.
- Breakeven: This strategy breaks even if, at expiration, the stock price is either above the call strike price or below the put strike price by the amount of premium paid. At either of those levels, one option's intrinsic value will equal the premium paid for both options while the other option will be expiring worthless.
- Assignment / expiration: None. The investor is in control. If the options are held into expiration, one of them may be subject to auto-exercise.

## Greeks and time

- Volatility: An increase in implied volatility, all other things equal, would have a very positive impact on this strategy. Even if the stock price holds steady, a quick rise in implied volatility would push up the value of both options and might allow the investor to close out the position for a profit well before expiration.
- Time decay: The passage of time, all other things equal, will have a very negative impact on this strategy. Because the strategy consists of being long two options, every day that passes without a move in the stock's price will cause their value to suffer a significant erosion of value.

## Evidence

### Definition

- [[Source — Long Strangle (Long Combination)]] · `Long Strangle (Long Combination)` · lines 1–4
  > This strategy profits if the stock price moves sharply in either direction during the life of the option.
- [[Source — Long Strangle (Long Combination)]] · `Description` · lines 5–8
  > This strategy typically involves buying an out-of-the money call option and an out-of-the-money put option with the same expiration date.
- [[Source — Long Strangle (Long Combination)]] · `Summary` · lines 13–16
  > This strategy does best if the stock price moves sharply in either direction during the life of the options.

### Legs

- [[Source — Long Strangle (Long Combination)]] · `Example` · lines 25–37
  > - Long 1 XYZ 65 call - Long 1 XYZ 55 put MAXIMUM GAIN - Unlimited MAXIMUM LOSS - Net premium paid

### Objective

- [[Source — Long Strangle (Long Combination)]] · `Description` · lines 5–8
  > This strategy typically involves buying an out-of-the money call option and an out-of-the-money put option with the same expiration date.
- [[Source — Long Strangle (Long Combination)]] · `Motivation` · lines 17–24
  > The strategy hopes to capture a quick increase in implied volatility or a big move in the underlying stock price during the life of the options. ; Profit increases below 50 and above 70") Net Position (at expiration)

### Market Outlook

- [[Source — Long Strangle (Long Combination)]] · `Outlook` · lines 9–12
  > The investor is looking for a sharp move in the underlying stock, either up or down, during the life of the options.

### Max Gain

- [[Source — Long Strangle (Long Combination)]] · `Example` · lines 25–37
  > - Long 1 XYZ 65 call - Long 1 XYZ 55 put MAXIMUM GAIN - Unlimited MAXIMUM LOSS - Net premium paid
- [[Source — Long Strangle (Long Combination)]] · `Max Gain` · lines 48–51
  > The maximum gain is unlimited. The maximum gain occurs if the underlying stock goes to infinity, and a very substantial gain would occur if the stock became worthless. The gross profit at expiration would be the difference between the stock's price and either the call strike price if the stock price is higher or the pu

### Max Loss

- [[Source — Long Strangle (Long Combination)]] · `Example` · lines 25–37
  > - Long 1 XYZ 65 call - Long 1 XYZ 55 put MAXIMUM GAIN - Unlimited MAXIMUM LOSS - Net premium paid
- [[Source — Long Strangle (Long Combination)]] · `Max Loss` · lines 44–47
  > The maximum loss is limited. The maximum loss occurs if the underlying stock remains between the strike prices until expiration. If at expiration the stock's price is between the strikes, both options will expire worthless and the entire premium paid will have been lost.

### Breakeven

- [[Source — Long Strangle (Long Combination)]] · `Breakeven` · lines 56–63
  > This strategy breaks even if, at expiration, the stock price is either above the call strike price or below the put strike price by the amount of premium paid. At either of those levels, one option's intrinsic value will equal the premium paid for both options while the other option will be expiring worthless. Upside b

### Volatility Effect

- [[Source — Long Strangle (Long Combination)]] · `Volatility` · lines 64–67
  > An increase in implied volatility, all other things equal, would have a very positive impact on this strategy. Even if the stock price holds steady, a quick rise in implied volatility would push up the value of both options and might allow the investor to close out the position for a profit well before expiration.

### Time Decay Effect

- [[Source — Long Strangle (Long Combination)]] · `Time Decay` · lines 68–71
  > The passage of time, all other things equal, will have a very negative impact on this strategy. Because the strategy consists of being long two options, every day that passes without a move in the stock's price will cause their value to suffer a significant erosion of value.

### Assignment Or Expiration Risk

- [[Source — Long Strangle (Long Combination)]] · `Assignment Risk` · lines 72–75
  > None. The investor is in control.
- [[Source — Long Strangle (Long Combination)]] · `Expiration Risk` · lines 76–79
  > If the options are held into expiration, one of them may be subject to auto-exercise.

### Suitability Constraints

- [[Source — Long Strangle (Long Combination)]] · `Motivation` · lines 17–24
  > The strategy hopes to capture a quick increase in implied volatility or a big move in the underlying stock price during the life of the options. ; Profit increases below 50 and above 70") Net Position (at expiration)
- [[Source — Long Strangle (Long Combination)]] · `Comments` · lines 80–83
  > This strategy is really a race between time decay and volatility. The passage of time is a constant that erodes the position's value a little bit every day. Volatility is the storm which might blow in at any moment, or which might never occur at all.


See the [[index|Wiki Index]].
