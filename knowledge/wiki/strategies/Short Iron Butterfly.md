---
type: entity
title: Short Iron Butterfly
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - entity
  - strategy
  - iron-butterfly
entity_type: option-strategy
aliases:
  - short iron butterfly
  - iron butterfly
sources:
  - "[[Source — Short Iron Butterfly]]"
related: []
---

# Short Iron Butterfly

Collect credit for a short at-the-money straddle (strikes near the current stock price) hedged by a long out-of-the-money strangle (strikes farther from the current stock price); profits if price stays near the body.

- Underlying: equity option
- Knowledge id: `strategy.short_iron_butterfly`
- Review status: `published`
- Futu category: 铁蝶式策略 / Iron Butterfly

## Legs

- long lower wing put (put option)
- short middle-strike put (put option)
- short middle-strike call (call option)
- long upper wing call, equidistant (call option)

## Meaning

Collect credit for a short at-the-money straddle (strikes near the current stock price) hedged by a long out-of-the-money strangle (strikes farther from the current stock price); profits if price stays near the body.

## Scenario

Neutral; wants the underlying near the body at expiration.

For short-premium traders who need defined wings and can handle assignment on the short body options.

## Method

- Maximum profit: The maximum gain would occur should the underlying stock be at the body of the butterfly at expiration. In that case all the options would expire worthless, and the premium received to initiate the position could be pocketed.
- Maximum loss: The maximum loss would occur should the underlying stock be outside the wings at expiration. In that case either both calls or both puts would be in-the-money.
- Break-even: The strategy breaks even if at expiration the underlying stock is either above or below the body of the butterfly by the amount of premium received to initiate the position.
- Assignment / expiration: The short options that form the body of the butterfly are subject to exercise at any time, while the investor decides if and when to exercise the wings. If an early exercise occurs at the body, the investor can choose whether to close out the resulting position in the market or to exercise one of their options (put or  This strategy has expiration risk. If at expiration the stock is trading near the body of the butterfly, the investor faces uncertainty as to whether or not they will be assigned.

## How the price reacts to volatility and time

- Volatility: An increase in implied volatility, all other things equal, would have a negative impact on this strategy.
- Time decay: The passage of time, all other things equal, will have a positive effect on this strategy.

## Evidence

### Definition

- [[Source — Short Iron Butterfly]] · `Short Iron Butterfly` · lines 1–4
  > This strategy profits if the underlying stock is inside the wings of the iron butterfly at expiration.
- [[Source — Short Iron Butterfly]] · `Description` · lines 5–8
  > A short iron butterfly consists of being long a call at an upper strike, short a call and short a put at a middle strike, and long a put at a lower strike. The upper and lower strikes (wings) must both be equidistant from the middle strike (body), and all the options must be the same expiration. An alternative way to t
- [[Source — Short Iron Butterfly]] · `Summary` · lines 13–20
  > This strategy works better if the underlying stock is inside the wings of the iron butterfly at expiration. ; Max loss at 55 and 65 (red dots)") Net Position (at expiration)

### Legs

- [[Source — Short Iron Butterfly]] · `Example` · lines 21–35
  > - Long 1 XYZ 65 call - Short 1 XYZ 60 call - Short 1 XYZ 60 put - Long 1 XYZ 55 put MAXIMUM GAIN - Net premium received MAXIMUM LOSS - High strike - middle strike - net premium received

### Objective

- [[Source — Short Iron Butterfly]] · `Description` · lines 5–8
  > A short iron butterfly consists of being long a call at an upper strike, short a call and short a put at a middle strike, and long a put at a lower strike. The upper and lower strikes (wings) must both be equidistant from the middle strike (body), and all the options must be the same expiration. An alternative way to t
- [[Source — Short Iron Butterfly]] · `Motivation` · lines 36–39
  > Earn income by predicting a period of neutral movement in the underlying.

### Market Outlook

- [[Source — Short Iron Butterfly]] · `Outlook` · lines 9–12
  > The investor is looking for the underlying stock to trade in a narrow range during the life of the options.

### Max Gain

- [[Source — Short Iron Butterfly]] · `Example` · lines 21–35
  > - Long 1 XYZ 65 call - Short 1 XYZ 60 call - Short 1 XYZ 60 put - Long 1 XYZ 55 put MAXIMUM GAIN - Net premium received MAXIMUM LOSS - High strike - middle strike - net premium received
- [[Source — Short Iron Butterfly]] · `Max Gain` · lines 48–51
  > The maximum gain would occur should the underlying stock be at the body of the butterfly at expiration. In that case all the options would expire worthless, and the premium received to initiate the position could be pocketed.

### Max Loss

- [[Source — Short Iron Butterfly]] · `Example` · lines 21–35
  > - Long 1 XYZ 65 call - Short 1 XYZ 60 call - Short 1 XYZ 60 put - Long 1 XYZ 55 put MAXIMUM GAIN - Net premium received MAXIMUM LOSS - High strike - middle strike - net premium received
- [[Source — Short Iron Butterfly]] · `Max Loss` · lines 44–47
  > The maximum loss would occur should the underlying stock be outside the wings at expiration. In that case either both calls or both puts would be in-the-money. The loss would be the difference between the body and either wing, less the premium received for initiating the position.

### Breakeven

- [[Source — Short Iron Butterfly]] · `Breakeven` · lines 56–59
  > The strategy breaks even if at expiration the underlying stock is either above or below the body of the butterfly by the amount of premium received to initiate the position.

### Volatility Effect

- [[Source — Short Iron Butterfly]] · `Volatility` · lines 60–63
  > An increase in implied volatility, all other things equal, would have a negative impact on this strategy.

### Time Decay Effect

- [[Source — Short Iron Butterfly]] · `Time Decay` · lines 64–67
  > The passage of time, all other things equal, will have a positive effect on this strategy.

### Assignment Or Expiration Risk

- [[Source — Short Iron Butterfly]] · `Assignment Risk` · lines 68–75
  > The short options that form the body of the butterfly are subject to exercise at any time, while the investor decides if and when to exercise the wings. If an early exercise occurs at the body, the investor can choose whether to close out the resulting position in the market or to exercise one of their options (put or
- [[Source — Short Iron Butterfly]] · `Expiration Risk` · lines 76–79
  > This strategy has expiration risk. If at expiration the stock is trading near the body of the butterfly, the investor faces uncertainty as to whether or not they will be assigned. Should the exercise activity be other than expected, the investor could be unexpectedly long or short the stock on the Monday following expi

### Suitability Constraints

- [[Source — Short Iron Butterfly]] · `Motivation` · lines 36–39
  > Earn income by predicting a period of neutral movement in the underlying.
- [[Source — Short Iron Butterfly]] · `Comments` · lines 80–83
  > N/A


See the [[index|Wiki Index]].
