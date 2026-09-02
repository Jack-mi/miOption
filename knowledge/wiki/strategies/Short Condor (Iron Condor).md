---
type: entity
title: Short Condor (Iron Condor)
status: evergreen
created: 2026-09-02
updated: 2026-09-02
tags:
  - entity
  - strategy
  - iron-condor
entity_type: option-strategy
aliases:
  - iron condor
  - short iron condor
  - short condor
sources:
  - "[[Source — Short Condor (Iron Condor)]]"
related: []
---

# Short Condor (Iron Condor)

Collect credit when expecting the underlying to stay between the short put and short call strikes through expiration.

- Underlying: equity option
- Knowledge id: `strategy.short_iron_condor`
- Review status: `published`
- Futu category: 铁鹰式策略 / Iron Condor

## Legs

- long lower wing put (put option)
- short higher put shoulder (put option)
- short lower call shoulder (call option)
- long upper wing call (call option)

## Meaning

Collect credit when expecting the underlying to stay between the short put and short call strikes through expiration.

## Scenario

Neutral / range-bound inside the inner wings; rising IV generally hurts.

For short-premium traders seeking a wider profit zone than an iron butterfly with defined wing risk.

## Method

- Max gain: The maximum gain would occur should the underlying stock be between the lower call strike and upper put strike at expiration. In that case all the options would expire worthless, and the premium received to initiate the position could be pocketed.
- Max loss: The maximum loss would occur should the underlying stock be above the upper call strike or below the lower put strike at expiration. In that case either both calls or both puts would be in-the-money.
- Breakeven: This strategy breaks even if at expiration the underlying stock is either above the lower call strike or below the upper put strike by the amount of the premium received to initiate the position. Upside breakeven = lower call strike + premiums received
Downside breakeven = upper put strike - premiums received
- Assignment / expiration: The short options that form the shoulders of the condor's wings are subject to exercise at any time, while the investor decides if and when to exercise the wingtips. If an early exercise occurs at either shoulder, the investor can choose whether to close out the resulting position in the market or to exercise the appro If at expiration the stock is trading near either shoulder the investor would face uncertainty as to whether or not they would be assigned. Should the exercise activity be other than expected, the investor could be unexpectedly long or short the stock on the Monday following expiration and hence subject to an adverse m

## Greeks and time

- Volatility: An increase in implied volatility, all other things equal, would have a negative impact on this strategy.
- Time decay: The passage of time, all other things equal, will have a positive effect on this strategy.

## Evidence

### Definition

- [[Source — Short Condor (Iron Condor)]] · `Short Condor (Iron Condor)` · lines 1–4
  > This strategy profits if the underlying stock is inside the inner wings at expiration.
- [[Source — Short Condor (Iron Condor)]] · `Description` · lines 5–10
  > To construct a short condor, the investor sells one call while buying another call with a higher strike and sells one put while buying another put with a lower strike. Typically, the call strikes are above and the put strikes below the current level of underlying stock, and the distance between the call strikes equals
- [[Source — Short Condor (Iron Condor)]] · `Summary` · lines 15–22
  > This strategy profits if the underlying stock is inside the inner wings at expiration. , Long 50 put & 70 call (red dots); Max loss between 55-65, Max profit below 50 or above 70") Net Position (at expiration)

### Legs

- [[Source — Short Condor (Iron Condor)]] · `Example` · lines 23–37
  > - Long 1 XYZ 70 call - Short 1 XYZ 65 call - Short 1 XYZ 55 put - Long 1 XYZ 50 put MAXIMUM GAIN - Net premium received MAXIMUM LOSS - (High call strike - low call strike) OR (High put strike- low put strike) - net premium received

### Objective

- [[Source — Short Condor (Iron Condor)]] · `Description` · lines 5–10
  > To construct a short condor, the investor sells one call while buying another call with a higher strike and sells one put while buying another put with a lower strike. Typically, the call strikes are above and the put strikes below the current level of underlying stock, and the distance between the call strikes equals
- [[Source — Short Condor (Iron Condor)]] · `Motivation` · lines 38–41
  > The investor hopes the underlying stock will stay within a certain range by expiration.

### Market Outlook

- [[Source — Short Condor (Iron Condor)]] · `Outlook` · lines 11–14
  > The investor is hoping for underlying stock to trade in narrow range during the life of the options.

### Max Gain

- [[Source — Short Condor (Iron Condor)]] · `Example` · lines 23–37
  > - Long 1 XYZ 70 call - Short 1 XYZ 65 call - Short 1 XYZ 55 put - Long 1 XYZ 50 put MAXIMUM GAIN - Net premium received MAXIMUM LOSS - (High call strike - low call strike) OR (High put strike- low put strike) - net premium received
- [[Source — Short Condor (Iron Condor)]] · `Max Gain` · lines 50–53
  > The maximum gain would occur should the underlying stock be between the lower call strike and upper put strike at expiration. In that case all the options would expire worthless, and the premium received to initiate the position could be pocketed.

### Max Loss

- [[Source — Short Condor (Iron Condor)]] · `Example` · lines 23–37
  > - Long 1 XYZ 70 call - Short 1 XYZ 65 call - Short 1 XYZ 55 put - Long 1 XYZ 50 put MAXIMUM GAIN - Net premium received MAXIMUM LOSS - (High call strike - low call strike) OR (High put strike- low put strike) - net premium received
- [[Source — Short Condor (Iron Condor)]] · `Max Loss` · lines 46–49
  > The maximum loss would occur should the underlying stock be above the upper call strike or below the lower put strike at expiration. In that case either both calls or both puts would be in-the-money. The loss would be the difference between either the call strikes or the put strikes (whichever are in-the-money), less t

### Breakeven

- [[Source — Short Condor (Iron Condor)]] · `Breakeven` · lines 58–65
  > This strategy breaks even if at expiration the underlying stock is either above the lower call strike or below the upper put strike by the amount of the premium received to initiate the position. Upside breakeven = lower call strike + premiums received Downside breakeven = upper put strike - premiums received

### Volatility Effect

- [[Source — Short Condor (Iron Condor)]] · `Volatility` · lines 66–69
  > An increase in implied volatility, all other things equal, would have a negative impact on this strategy.

### Time Decay Effect

- [[Source — Short Condor (Iron Condor)]] · `Time Decay` · lines 70–73
  > The passage of time, all other things equal, will have a positive effect on this strategy.

### Assignment Or Expiration Risk

- [[Source — Short Condor (Iron Condor)]] · `Assignment Risk` · lines 74–81
  > The short options that form the shoulders of the condor's wings are subject to exercise at any time, while the investor decides if and when to exercise the wingtips. If an early exercise occurs at either shoulder, the investor can choose whether to close out the resulting position in the market or to exercise the appro
- [[Source — Short Condor (Iron Condor)]] · `Expiration Risk` · lines 82–85
  > If at expiration the stock is trading near either shoulder the investor would face uncertainty as to whether or not they would be assigned. Should the exercise activity be other than expected, the investor could be unexpectedly long or short the stock on the Monday following expiration and hence subject to an adverse m

### Suitability Constraints

- [[Source — Short Condor (Iron Condor)]] · `Motivation` · lines 38–41
  > The investor hopes the underlying stock will stay within a certain range by expiration.
- [[Source — Short Condor (Iron Condor)]] · `Comments` · lines 86–89
  > N/A


See the [[index|Wiki Index]].
