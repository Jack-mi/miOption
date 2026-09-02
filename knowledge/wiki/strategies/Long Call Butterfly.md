---
type: entity
title: Long Call Butterfly
status: evergreen
created: 2026-09-02
updated: 2026-09-02
tags:
  - entity
  - strategy
  - butterfly
entity_type: option-strategy
aliases:
  - long call butterfly
  - butterfly
sources:
  - "[[Source — Long Call Butterfly]]"
related:
  - "[[Long Put Butterfly]]"
---

# Long Call Butterfly

Profit if the underlying finishes near the body strike at expiration, with defined risk equal to the net debit.

- Underlying: equity option
- Knowledge id: `strategy.long_call_butterfly`
- Review status: `published`
- Futu category: 蝶式策略 / Butterfly

## Legs

- long one lower-strike wing (call option)
- short two middle-strike body calls (call option)
- long one upper-strike wing, equidistant, same expiration (call option)

## Meaning

Profit if the underlying finishes near the body strike at expiration, with defined risk equal to the net debit.

## Scenario

Neutral / low realized move into expiration around the body.

For investors seeking defined-risk short-volatility style payoff who accept high expiration pin risk at the body.

## Method

- Max gain: The maximum profit would occur should the underlying stock be at the middle strike at expiration. In that case, the long call with the lower strike would be in-the-money and all the other options would expire worthless.
- Max loss: The maximum loss would occur should the underlying stock be outside the wings at expiration. If the stock were below the lower strike all the options would expire worthless; if above the upper strike all the options would be exercised and offset each other for a zero profit.
- Breakeven: The strategy breaks even if at expiration the underlying stock is above the lower strike or below the upper strike by the amount of premium paid to initiate the position.
- Assignment / expiration: Yes. The short calls that form the body of the butterfly are subject to exercise at any time, while the investor decides if and when to exercise the wings. Yes. This strategy has an extremely high expiration risk.

## Greeks and time

- Volatility: An increase in implied volatility, all other things equal, will usually have a slightly negative impact on this strategy.
- Time decay: The passage of time, all other things equal, will usually have a positive impact on this strategy if the body of the butterfly is at-the-money, and a negative impact if the body is away from the money.

## Evidence

### Definition

- [[Source — Long Call Butterfly]] · `Long Call Butterfly` · lines 1–4
  > This strategy profits if the underlying stock is at the body of the butterfly at expiration.
- [[Source — Long Call Butterfly]] · `Description` · lines 5–8
  > Combining two short calls at a middle strike, and one long call each at a lower and upper strike creates a long call butterfly. The upper and lower strikes (wings) must both be equidistant from the middle strike (body), and all the options must have the same expiration date.
- [[Source — Long Call Butterfly]] · `Summary` · lines 13–16
  > This strategy generally profits if the underlying stock is at the body of the butterfly at expiration.

### Legs

- [[Source — Long Call Butterfly]] · `Example` · lines 25–38
  > - Long 1 XYZ 65 call - Short 2 XYZ 60 calls - Long 1 XYZ 55 call MAXIMUM GAIN - High strike - middle strike - net premium paid MAXIMUM LOSS - Net premium paid

### Objective

- [[Source — Long Call Butterfly]] · `Description` · lines 5–8
  > Combining two short calls at a middle strike, and one long call each at a lower and upper strike creates a long call butterfly. The upper and lower strikes (wings) must both be equidistant from the middle strike (body), and all the options must have the same expiration date.
- [[Source — Long Call Butterfly]] · `Motivation` · lines 17–24
  > Profit by correctly predicting the stock price at expiration. , Short 2x 60 calls (green dot); Max profit at 60, Max loss below 55 or above 65") Net Position (at expiration)

### Market Outlook

- [[Source — Long Call Butterfly]] · `Outlook` · lines 9–12
  > Looking for the underlying stock to achieve a specific price target at the expiration of the options.

### Max Gain

- [[Source — Long Call Butterfly]] · `Example` · lines 25–38
  > - Long 1 XYZ 65 call - Short 2 XYZ 60 calls - Long 1 XYZ 55 call MAXIMUM GAIN - High strike - middle strike - net premium paid MAXIMUM LOSS - Net premium paid
- [[Source — Long Call Butterfly]] · `Max Gain` · lines 51–54
  > The maximum profit would occur should the underlying stock be at the middle strike at expiration. In that case, the long call with the lower strike would be in-the-money and all the other options would expire worthless. The profit would be the difference between the lower and middle strike (the wing and the body), less

### Max Loss

- [[Source — Long Call Butterfly]] · `Example` · lines 25–38
  > - Long 1 XYZ 65 call - Short 2 XYZ 60 calls - Long 1 XYZ 55 call MAXIMUM GAIN - High strike - middle strike - net premium paid MAXIMUM LOSS - Net premium paid
- [[Source — Long Call Butterfly]] · `Max Loss` · lines 47–50
  > The maximum loss would occur should the underlying stock be outside the wings at expiration. If the stock were below the lower strike all the options would expire worthless; if above the upper strike all the options would be exercised and offset each other for a zero profit. In either case the premium paid to initiate

### Breakeven

- [[Source — Long Call Butterfly]] · `Breakeven` · lines 59–62
  > The strategy breaks even if at expiration the underlying stock is above the lower strike or below the upper strike by the amount of premium paid to initiate the position.

### Volatility Effect

- [[Source — Long Call Butterfly]] · `Volatility` · lines 63–66
  > An increase in implied volatility, all other things equal, will usually have a slightly negative impact on this strategy.

### Time Decay Effect

- [[Source — Long Call Butterfly]] · `Time Decay` · lines 67–70
  > The passage of time, all other things equal, will usually have a positive impact on this strategy if the body of the butterfly is at-the-money, and a negative impact if the body is away from the money.

### Assignment Or Expiration Risk

- [[Source — Long Call Butterfly]] · `Assignment Risk` · lines 71–76
  > Yes. The short calls that form the body of the butterfly are subject to exercise at any time, while the investor decides if and when to exercise the wings. The components of this position form an integral unit, and any early exercise could be disruptive to the strategy. In general, since the cost of carry makes it opti
- [[Source — Long Call Butterfly]] · `Expiration Risk` · lines 77–80
  > Yes. This strategy has an extremely high expiration risk. Consider that the maximum profit occurs when at expiration if the stock is trading right at the body of the butterfly. Presumably the investor will choose to exercise their in-the-money wing, but there is no way of knowing for sure whether none, one or both of t

### Suitability Constraints

- [[Source — Long Call Butterfly]] · `Motivation` · lines 17–24
  > Profit by correctly predicting the stock price at expiration. , Short 2x 60 calls (green dot); Max profit at 60, Max loss below 55 or above 65") Net Position (at expiration)
- [[Source — Long Call Butterfly]] · `Comments` · lines 81–84
  > N/A

## See also

- related to: [[Long Put Butterfly]]

See the [[index|Wiki Index]].
