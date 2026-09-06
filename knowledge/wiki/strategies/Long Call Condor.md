---
type: entity
title: Long Call Condor
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - entity
  - strategy
  - condor
entity_type: option-strategy
aliases:
  - long call condor
  - call condor
sources:
  - "[[Source — Long Call Condor]]"
related: []
---

# Long Call Condor

Profit if the underlying finishes between the two short strikes, with a wider sweet spot than a butterfly.

- Underlying: equity option
- Knowledge id: `strategy.long_call_condor`
- Review status: `published`
- Futu category: 鹰式策略 / Condor

## Legs

- long lowest strike (call option)
- short lower middle strike (call option)
- short upper middle strike (call option)
- long highest strike, same expiration (call option)

## Meaning

Profit if the underlying finishes between the two short strikes, with a wider sweet spot than a butterfly.

## Scenario

Neutral / range-bound between the short strikes at expiration.

For defined-risk traders wanting a wider profit zone than a butterfly, still with multi-leg assignment complexity.

## Method

- Maximum profit: The maximum gain would occur if the underlying security is between the two short call strikes at expiration. In that case, the lower strike long call is worth its maximum value.
- Maximum loss: In all circumstances the maximum loss is limited to the net debit paid (assuming the distances between all four strikes prices are equal). The maximum loss would occur should the underlying be below the lowest long call strike at expiration or at or above the highest long call strike.
- Break-even: There are two breakeven points. This strategy breaks even if at expiration the underlying security is above the lower long call strike plus the amount of premium paid to initiate the position or if the underlying is below the highest long call strike less the premium paid.
- Assignment / expiration: In the case of American style options, the short options that form the body of the long call condor are subject to assignment at any time. Should early assignment occur on the short call options, the investor can exercise the appropriate long option but may be required to borrow or finance stock for one business day. Investors face an uncertainty when the underlying trades above both short call strikes but below the highest long call strike. In this case, the investor is likely to be assigned on both short calls resulting in a short position that is unhedged following expiration.

## How the price reacts to volatility and time

- Volatility: All other things being equal, an increase in implied volatility if the underlying is between the two short strikes when established would have a negative impact on this strategy. As with most strategies however, the impact of implied volatility changes will depend on strike selection relative to the stock price when th
- Time decay: All other things being equal, the passage of time will have a positive impact on this strategy.

## Evidence

### Definition

- [[Source — Long Call Condor]] · `Long Call Condor` · lines 1–4
  > This strategy profits if the underlying security is between the two short call strikes at expiration.
- [[Source — Long Call Condor]] · `Description` · lines 5–10
  > A long call condor consists of four different call options of the same expiration. The strategy is constructed of 1 long in-the-money call, 1 short higher middle strike in-the-money call, 1 short middle out-of-money call, 1 long highest strike out-of-money call. An alternative way to think about this strategy is an in-
- [[Source — Long Call Condor]] · `Summary` · lines 15–22
  > This strategy profits if the underlying security is between the two short call strikes at expiration. , Short 60 & 65 calls (green dots); Max profit between 60-65, Max loss below 55 or above 70") Net Position (at expiration)

### Legs

- [[Source — Long Call Condor]] · `Example` · lines 23–37
  > - Long 1 XYZ 55 Call - Short 1 XYZ 60 Call - Short 1 XYZ 65 Call - Long 1 XYZ 70 Call MAXIMUM GAIN - (Lowest, short call strike – lowest, long call strike) – Net premium paid MAXIMUM LOSS - Net premium paid

### Objective

- [[Source — Long Call Condor]] · `Description` · lines 5–10
  > A long call condor consists of four different call options of the same expiration. The strategy is constructed of 1 long in-the-money call, 1 short higher middle strike in-the-money call, 1 short middle out-of-money call, 1 long highest strike out-of-money call. An alternative way to think about this strategy is an in-
- [[Source — Long Call Condor]] · `Motivation` · lines 38–41
  > Anticipating minimal price movement in the underlying during the lifetime of the options.

### Market Outlook

- [[Source — Long Call Condor]] · `Outlook` · lines 11–14
  > The long call condor investor is normally looking for little or no movement in the underlying.

### Max Gain

- [[Source — Long Call Condor]] · `Example` · lines 23–37
  > - Long 1 XYZ 55 Call - Short 1 XYZ 60 Call - Short 1 XYZ 65 Call - Long 1 XYZ 70 Call MAXIMUM GAIN - (Lowest, short call strike – lowest, long call strike) – Net premium paid MAXIMUM LOSS - Net premium paid
- [[Source — Long Call Condor]] · `Maximum Gain` · lines 52–55
  > The maximum gain would occur if the underlying security is between the two short call strikes at expiration. In that case, the lower strike long call is worth its maximum value. The profit would be the difference between the strikes less the premium paid to initiate the position.

### Max Loss

- [[Source — Long Call Condor]] · `Example` · lines 23–37
  > - Long 1 XYZ 55 Call - Short 1 XYZ 60 Call - Short 1 XYZ 65 Call - Long 1 XYZ 70 Call MAXIMUM GAIN - (Lowest, short call strike – lowest, long call strike) – Net premium paid MAXIMUM LOSS - Net premium paid
- [[Source — Long Call Condor]] · `Maximum Loss` · lines 48–51
  > In all circumstances the maximum loss is limited to the net debit paid (assuming the distances between all four strikes prices are equal). The maximum loss would occur should the underlying be below the lowest long call strike at expiration or at or above the highest long call strike. At the lowest strike all the optio

### Breakeven

- [[Source — Long Call Condor]] · `Breakeven` · lines 60–67
  > There are two breakeven points. This strategy breaks even if at expiration the underlying security is above the lower long call strike plus the amount of premium paid to initiate the position or if the underlying is below the highest long call strike less the premium paid. Downside breakeven = lowest long call strike +

### Volatility Effect

- [[Source — Long Call Condor]] · `Volatility` · lines 68–71
  > All other things being equal, an increase in implied volatility if the underlying is between the two short strikes when established would have a negative impact on this strategy. As with most strategies however, the impact of implied volatility changes will depend on strike selection relative to the stock price when th

### Time Decay Effect

- [[Source — Long Call Condor]] · `Time Decay` · lines 72–75
  > All other things being equal, the passage of time will have a positive impact on this strategy.

### Assignment Or Expiration Risk

- [[Source — Long Call Condor]] · `Assignment Risk` · lines 76–81
  > In the case of American style options, the short options that form the body of the long call condor are subject to assignment at any time. Should early assignment occur on the short call options, the investor can exercise the appropriate long option but may be required to borrow or finance stock for one business day. T
- [[Source — Long Call Condor]] · `Expiration Risk` · lines 82–85
  > Investors face an uncertainty when the underlying trades above both short call strikes but below the highest long call strike. In this case, the investor is likely to be assigned on both short calls resulting in a short position that is unhedged following expiration. Investors in this case would be subject to an advers

### Suitability Constraints

- [[Source — Long Call Condor]] · `Motivation` · lines 38–41
  > Anticipating minimal price movement in the underlying during the lifetime of the options.
- [[Source — Long Call Condor]] · `Comments` · lines 86–91
  > One important consideration of the long call condor is assignment risk. If the underlying is above both short call strikes yet below the highest long call strike, an assignment would result in both short calls delivering stock yet only one of the long calls being exercised. Thus, the investor would end up net short the


See the [[index|Wiki Index]].
