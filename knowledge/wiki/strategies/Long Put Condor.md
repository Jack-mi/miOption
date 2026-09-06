---
type: entity
title: Long Put Condor
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - entity
  - strategy
  - condor
entity_type: option-strategy
aliases:
  - long put condor
  - put condor
sources:
  - "[[Source — Long Put Condor]]"
related: []
---

# Long Put Condor

Profit if the underlying finishes between the two short puts at expiration, with defined risk.

- Underlying: equity option
- Knowledge id: `strategy.long_put_condor`
- Review status: `published`
- Futu category: 鹰式策略 / Condor

## Legs

- long lowest strike (put option)
- short lower middle strike (put option)
- short upper middle strike (put option)
- long highest strike, same expiration (put option)

## Meaning

Profit if the underlying finishes between the two short puts at expiration, with defined risk.

## Scenario

Neutral / range-bound between the short put strikes at expiration.

For defined-risk traders using puts to express a wide middle sweet spot into expiration.

## Method

- Maximum profit: The maximum gain would occur if the underlying security is between the two short put strikes at expiration. In that case, the higher strike long put is worth its maximum value.
- Maximum loss: In all circumstances the maximum loss is limited to the net debit paid (assuming the distances between all four strikes prices are equal). The maximum loss would occur should the underlying be above the highest long put strike at expiration or at or below the lowest long put strike.
- Break-even: There are two breakeven points. This strategy breaks even if at expiration the underlying security is below the highest long put strike less the amount of premium paid to initiate the position or if the underlying is above the lowest long put strike plus the premium paid.
- Assignment / expiration: In the case of American style options, the short options that form the body of the long put condor are subject to assignment at any time. Should early assignment occur on the short put options, the investor can exercise the appropriate long option but may be required to borrow or finance stock for one business day. Investors face an uncertainty when the underlying trades below both short put strikes but above the lowest long put strike. In this case, the investor is likely to be assigned on both short puts resulting in a long position that is unhedged following expiration.

## How the price reacts to volatility and time

- Volatility: All other things being equal, an increase in implied volatility if the underlying is between the two short strikes when established would have a negative impact on this strategy. As with most strategies however, the impact of implied volatility changes will depend on strike selection relative to the stock price when th
- Time decay: All other things being equal, the passage of time will have a positive effect on this strategy.

## Evidence

### Definition

- [[Source — Long Put Condor]] · `Long Put Condor` · lines 1–4
  > This strategy profits if the underlying security is between the two short put strikes at expiration.
- [[Source — Long Put Condor]] · `Description` · lines 5–10
  > A long put condor consists of four different put options of the same expiration. The strategy is constructed of 1 long out-of-money put at the lowest strike, 1 short out-of-money put at the middle strike, 1 short put at a higher in-the-money strike and 1 long deeper in-the-money put at the highest strike. An alternativ
- [[Source — Long Put Condor]] · `Summary` · lines 15–22
  > This strategy profits if the underlying security is between the two short put strikes at expiration. , Short 60 & 65 puts (green dots); Max profit 60-65") Net Position (at expiration)

### Legs

- [[Source — Long Put Condor]] · `Example` · lines 23–37
  > - Long 1 XYZ 55 Put - Short 1 XYZ 60 Put - Short 1 XYZ 65 Put - Long 1 XYZ 70 Put MAXIMUM GAIN - (Highest long put strike – highest short put strike) - Net premium paid MAXIMUM LOSS - Net premium paid

### Objective

- [[Source — Long Put Condor]] · `Description` · lines 5–10
  > A long put condor consists of four different put options of the same expiration. The strategy is constructed of 1 long out-of-money put at the lowest strike, 1 short out-of-money put at the middle strike, 1 short put at a higher in-the-money strike and 1 long deeper in-the-money put at the highest strike. An alternativ
- [[Source — Long Put Condor]] · `Motivation` · lines 38–41
  > Anticipating minimal price movement in the underlying during the lifetime of the options.

### Market Outlook

- [[Source — Long Put Condor]] · `Outlook` · lines 11–14
  > The long put condor investor is normally looking for little or no movement in the underlying.

### Max Gain

- [[Source — Long Put Condor]] · `Example` · lines 23–37
  > - Long 1 XYZ 55 Put - Short 1 XYZ 60 Put - Short 1 XYZ 65 Put - Long 1 XYZ 70 Put MAXIMUM GAIN - (Highest long put strike – highest short put strike) - Net premium paid MAXIMUM LOSS - Net premium paid
- [[Source — Long Put Condor]] · `Max Gain` · lines 52–55
  > The maximum gain would occur if the underlying security is between the two short put strikes at expiration. In that case, the higher strike long put is worth its maximum value. The profit would be the difference between the strikes less the premium paid to initiate the position.

### Max Loss

- [[Source — Long Put Condor]] · `Example` · lines 23–37
  > - Long 1 XYZ 55 Put - Short 1 XYZ 60 Put - Short 1 XYZ 65 Put - Long 1 XYZ 70 Put MAXIMUM GAIN - (Highest long put strike – highest short put strike) - Net premium paid MAXIMUM LOSS - Net premium paid
- [[Source — Long Put Condor]] · `Max Loss` · lines 48–51
  > In all circumstances the maximum loss is limited to the net debit paid (assuming the distances between all four strikes prices are equal). The maximum loss would occur should the underlying be above the highest long put strike at expiration or at or below the lowest long put strike. At the highest strike all the option

### Breakeven

- [[Source — Long Put Condor]] · `Breakeven` · lines 60–67
  > There are two breakeven points. This strategy breaks even if at expiration the underlying security is below the highest long put strike less the amount of premium paid to initiate the position or if the underlying is above the lowest long put strike plus the premium paid. Downside breakeven = lower long put strike + pr

### Volatility Effect

- [[Source — Long Put Condor]] · `Volatility` · lines 68–71
  > All other things being equal, an increase in implied volatility if the underlying is between the two short strikes when established would have a negative impact on this strategy. As with most strategies however, the impact of implied volatility changes will depend on strike selection relative to the stock price when th

### Time Decay Effect

- [[Source — Long Put Condor]] · `Time Decay` · lines 72–75
  > All other things being equal, the passage of time will have a positive effect on this strategy.

### Assignment Or Expiration Risk

- [[Source — Long Put Condor]] · `Assignment Risk` · lines 76–81
  > In the case of American style options, the short options that form the body of the long put condor are subject to assignment at any time. Should early assignment occur on the short put options, the investor can exercise the appropriate long option but may be required to borrow or finance stock for one business day. The
- [[Source — Long Put Condor]] · `Expiration Risk` · lines 82–85
  > Investors face an uncertainty when the underlying trades below both short put strikes but above the lowest long put strike. In this case, the investor is likely to be assigned on both short puts resulting in a long position that is unhedged following expiration. Investors in this case would be subject to an adverse mov

### Suitability Constraints

- [[Source — Long Put Condor]] · `Motivation` · lines 38–41
  > Anticipating minimal price movement in the underlying during the lifetime of the options.
- [[Source — Long Put Condor]] · `Comments` · lines 86–91
  > One important consideration of the long put condor is assignment risk. If the underlying is below both short put strikes yet below the highest long put strike, an assignment would result in both short puts purchasing the underlying with only one of the long puts being exercised. Thus, the investor would end up net long


See the [[index|Wiki Index]].
