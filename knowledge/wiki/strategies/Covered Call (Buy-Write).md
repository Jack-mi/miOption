---
type: entity
title: Covered Call (Buy-Write)
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - entity
  - strategy
  - covered-stock
entity_type: option-strategy
aliases:
  - covered call
  - buy/write
sources:
  - "[[Source — Covered Call (Buy-Write)]]"
  - "[[Source — Optionistics Chapter 5 Covered Calls]]"
  - "[[Source — Optionistics Chapter 2 Growth]]"
related:
  - "[[Vega and implied volatility sensitivity]]"
  - "[[Equity options basics]]"
  - "[[Theta and time decay]]"
  - "[[Exercise, assignment, and expiration]]"
---

# Covered Call (Buy-Write)

Earn premium income while holding stock, accepting a cap on upside in exchange for a limited downside cushion. Optionistics also names the simultaneous stock-and-call fill a buy-write, and says the covered call has the same risk profile as a short put. P/L numbers stay with OIC.

- Underlying: equity stock
- Knowledge id: `strategy.covered_call`
- Review status: `published`
- Futu category: 股票担保 / Covered Stock

## Legs

- long equivalent amount to the short call; source example uses 100 shares (underlying stock)
- short one call in the source example (call option)

## Meaning

Earn premium income while holding stock, accepting a cap on upside in exchange for a limited downside cushion.

## Scenario

Steady or slightly rising stock price; not intended for a very bearish or very bullish investor.

Appropriate only where the investor accepts the preset sale price and can maintain the stock coverage for the short call.

## Method

- Max gain: Limited. In the source example: strike price minus stock purchase price plus premium received.
- Max loss: Limited but substantial. In the source example: stock purchase price minus premium received; the stock can become worthless.
- Breakeven: Starting stock price minus premium received.
- Assignment / expiration: Assignment is central to the strategy; the investor must be willing and able to sell stock at the strike. Early assignment and post-expiration assignment uncertainty require monitoring.

## Greeks and time

- Volatility: Neutral to slightly negative when implied volatility rises, all else equal, because buying back the short call can cost more.
- Time decay: Generally positive for the short call position because time erosion reduces the short call's time value, all else equal.

## Evidence

### Definition

- [[Source — Covered Call (Buy-Write)]] · `Covered Call (Buy/Write)` · lines 1–4
  > This strategy consists of writing a call that is covered by an equivalent long stock position.
- [[Source — Covered Call (Buy-Write)]] · `Description` · lines 5–18
  > An investor who buys or owns stock and writes call options in the equivalent amount can earn premium income without taking on additional risk. The premium received adds to the investor's bottom line regardless of outcome. It offers a small downside 'cushion' in the event the stock slides downward and can boost returns
- [[Source — Covered Call (Buy-Write)]] · `Summary` · lines 40–43
  > This strategy consists of writing a call that is covered by an equivalent long stock position. It provides a small hedge on the stock and allows an investor to earn premium income, in return for temporarily forfeiting much of the stock's upside potential.
- [[Source — Optionistics Chapter 5 Covered Calls]] · `Covered Calls`
  > A covered call is a strategy consisting of two positions, or legs. The covered call writer holds the stock and sells call options on that stock. This strategy is considered a low risk strategy because the obligation incurred by writing the call can be fulfilled by delivering the underlying stock.
- [[Source — Optionistics Chapter 5 Covered Calls]] · `Covered Calls`
  > Covered calls can be traded in a single complex strategy transaction known as a buy-write. A covered call has the same risk profile as a short put.
- [[Source — Optionistics Chapter 2 Growth]] · `Growth`
  > The covered call strategy consists of the purchase of a stock and a simultaneous sale of a call on that stock. The advantage of covered call writing is a more predictable flow of income. The disadvantage is that potential gains from the stock position are limited.

### Legs

- [[Source — Covered Call (Buy-Write)]] · `Example` · lines 19–35
  > - Long 100 shares XYZ stock - Short 1 XYZ 60 call MAXIMUM GAIN - Strike price - stock purchase price + premium received MAXIMUM LOSS - Stock purchase price - premium received (substantial) The covered call writer could select a higher, out-of-the-money strike price and preserve more of the stock's upside potential for

### Objective

- [[Source — Covered Call (Buy-Write)]] · `Description` · lines 5–18
  > An investor who buys or owns stock and writes call options in the equivalent amount can earn premium income without taking on additional risk. The premium received adds to the investor's bottom line regardless of outcome. It offers a small downside 'cushion' in the event the stock slides downward and can boost returns
- [[Source — Covered Call (Buy-Write)]] · `Motivation` · lines 44–51
  > The primary motive is to earn premium income, which has the effect of boosting overall returns on the stock and providing a measure of downside protection. The best candidates for covered calls are the stock owners who are perfectly willing to sell the shares if the stock rises and the calls are assigned. Stock owners

### Market Outlook

- [[Source — Covered Call (Buy-Write)]] · `Outlook` · lines 36–39
  > The covered call writer is looking for a steady or slightly rising stock price for at least the term of the option. This strategy not appropriate for a very bearish or a very bullish investor.

### Max Gain

- [[Source — Covered Call (Buy-Write)]] · `Example` · lines 19–35
  > - Long 100 shares XYZ stock - Short 1 XYZ 60 call MAXIMUM GAIN - Strike price - stock purchase price + premium received MAXIMUM LOSS - Stock purchase price - premium received (substantial) The covered call writer could select a higher, out-of-the-money strike price and preserve more of the stock's upside potential for
- [[Source — Covered Call (Buy-Write)]] · `Max Gain` · lines 62–71
  > The maximum gains on the strategy are limited. The total net gains depend in part on the call's intrinsic value when sold and on prior unrealized stock gains or losses. The maximum gains at expiration are limited by the strike price. If the stock is at the strike price, the covered call strategy itself reaches its peak

### Max Loss

- [[Source — Covered Call (Buy-Write)]] · `Example` · lines 19–35
  > - Long 100 shares XYZ stock - Short 1 XYZ 60 call MAXIMUM GAIN - Strike price - stock purchase price + premium received MAXIMUM LOSS - Stock purchase price - premium received (substantial) The covered call writer could select a higher, out-of-the-money strike price and preserve more of the stock's upside potential for
- [[Source — Covered Call (Buy-Write)]] · `Max Loss` · lines 56–61
  > The maximum loss is limited but substantial. The worst that can happen is for the stock to become worthless. In that case, the investor will have lost the entire value of the stock. However, that loss will be reduced somewhat by the premium income from selling the call option. It is also worth noting that the risk of l

### Breakeven

- [[Source — Covered Call (Buy-Write)]] · `Breakeven` · lines 86–91
  > Whether this strategy results in a profit or loss is largely determined by the purchase price of the stock, which may have occurred well in the past at a different price. Assume the stock and option positions were acquired simultaneously. If at expiration the position is still open and the investor wants to sell the st

### Volatility Effect

- [[Source — Covered Call (Buy-Write)]] · `Volatility` · lines 92–97
  > An increase in implied volatility would have a neutral to slightly negative impact on this strategy, all other things being equal. It would tend to increase the cost of buying the short call back to close the position. In that sense, greater volatility hurts this strategy as it does all short option positions. However,

### Time Decay Effect

- [[Source — Covered Call (Buy-Write)]] · `Time Decay` · lines 98–103
  > The passage of time has a positive impact on this strategy, all other things being equal. It tends to reduce the time value (and therefore overall price) of the short call, which would make it less expensive to close out if desired. As expiration approaches, an option tends to converge on its intrinsic value, which for

### Assignment Or Expiration Risk

- [[Source — Covered Call (Buy-Write)]] · `Assignment Risk` · lines 104–111
  > If the strategy was selected appropriately, there should be no problem here. A covered call strategy implicitly assumes the investor is willing and able to sell stock at the strike price (premium, in effect). Therefore, assignment simply allows the investor to liquidate the stock at the pre-set price and put the cash t
- [[Source — Covered Call (Buy-Write)]] · `Expiration Risk` · lines 112–119
  > For reasons described in 'Assignment Risk', there should be no issue with expiration risk, either. The appropriate use of this strategy implicitly assumes the investor is willing and able to sell stock at the strike price. It should not matter whether the option is exercised at expiration. If it is not, the investor is

### Suitability Constraints

- [[Source — Covered Call (Buy-Write)]] · `Motivation` · lines 44–51
  > The primary motive is to earn premium income, which has the effect of boosting overall returns on the stock and providing a measure of downside protection. The best candidates for covered calls are the stock owners who are perfectly willing to sell the shares if the stock rises and the calls are assigned. Stock owners
- [[Source — Covered Call (Buy-Write)]] · `Comments` · lines 120–125
  > As long as the short call position remains open, the investor isn't free to sell the stock. It would leave the calls uncovered and expose the investor to unlimited risk. To understand why, see the naked call strategy discussion. Unless they are completely indifferent to being assigned and to the cost of closing out the

## See also

- affects (outbound): [[Vega and implied volatility sensitivity]]
- requires (outbound): [[Equity options basics]]
- affects (outbound): [[Theta and time decay]]
- requires (outbound): [[Exercise, assignment, and expiration]]

See the [[index|Wiki Index]].
