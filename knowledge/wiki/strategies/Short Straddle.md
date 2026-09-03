---
type: entity
title: Short Straddle
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - entity
  - strategy
  - straddle
entity_type: option-strategy
aliases:
  - short straddle
sources:
  - "[[Source — Short Straddle]]"
  - "[[Source — Optionistics Chapter 5 Straddles]]"
related: []
---

# Short Straddle

Collect premium when expecting a narrow trading range and stable or falling implied volatility. Optionistics: collect two premiums; maximum profit when the underlying equals the strike. P/L stays OIC.

- Underlying: equity option
- Knowledge id: `strategy.short_straddle`
- Review status: `published`
- Futu category: 跨式策略 / Straddle

## Legs

- short ATM call (call option)
- short ATM put, same strike and expiration (put option)

## Meaning

Collect premium when expecting a narrow trading range and stable or falling implied volatility.

## Scenario

Neutral / range-bound; large moves either way are dangerous.

Only for investors who can margin short options and accept large or theoretically unlimited risk outside the range.

## Method

- Max gain: The maximum gain is limited to the premiums received at the outset. The best that can happen is for the stock price, at expiration, to be exactly at the strike price.
- Max loss: The maximum risk is unlimited. The worst that can happen is for the stock to rise to infinity, and the next-to-worst outcome is for the stock to fall to zero.
- Breakeven: This strategy breaks even if, at expiration, the stock price is either above or below the strike price by the total amount of premium income received. At either of those levels, one option's intrinsic value will equal the premium received for selling both options, while the other option will be expiring worthless.
- Assignment / expiration: Early assignment, while possible at any time, is more of a risk under certain circumstances: for a call, just before the stock goes ex-dividend; for a put, when it goes deep in-the-money. But the short straddle involves two short legs that could be assigned at any time during the life of the options, so investors shoul The investor cannot know for sure whether or not they were assigned until the Monday after expiration. If the stock hovers just above and below the strike price on the day before expiration, it is even conceivable that both options might be assigned.

## Greeks and time

- Volatility: Extremely important. This strategy's chances of success would be better if implied volatility were to fall.
- Time decay: Extremely important positive effect. Every day that passes without a move in the underlying stock price brings both options one day closer to expiring, which would obviously be the investor's best-case scenario.

## Evidence

### Definition

- [[Source — Short Straddle]] · `Short Straddle` · lines 1–4
  > This strategy involves selling a call option and a put option with the same expiration and strike price.
- [[Source — Short Straddle]] · `Description` · lines 5–16
  > A short straddle is a combination of writing uncovered calls (bearish) and writing uncovered puts (bullish), both with the same strike price and expiration. Together, they produce a position that predicts a narrow trading range for the underlying stock. Before there were options, it was difficult for investors to profi
- [[Source — Short Straddle]] · `Summary` · lines 36–39
  > This strategy involves selling a call option and a put option with the same expiration and strike price. It generally profits if the stock price and volatility remain steady.
- [[Source — Optionistics Chapter 5 Straddles]] · `Straddles`
  > The objective of a short straddle is to reap the premium of two option contracts, realizing the maximum profit when the price of the underlying stock equals the strike price. The short straddle trader profits when the stock price remains relatively stable.

### Legs

- [[Source — Short Straddle]] · `Example` · lines 17–29
  > - Short 1 XYZ 60 call - Short 1 XYZ 60 put MAXIMUM GAIN - Premium received MAXIMUM LOSS - Unlimited

### Objective

- [[Source — Short Straddle]] · `Description` · lines 5–16
  > A short straddle is a combination of writing uncovered calls (bearish) and writing uncovered puts (bullish), both with the same strike price and expiration. Together, they produce a position that predicts a narrow trading range for the underlying stock. Before there were options, it was difficult for investors to profi
- [[Source — Short Straddle]] · `Motivation` · lines 40–43
  > Earn income from selling premium.

### Market Outlook

- [[Source — Short Straddle]] · `Outlook` · lines 30–35
  > The strategy hopes for a steady stock price during the life of the options, and an even or declining level of implied volatility. Because of the substantial risk, should the stock price move out of the expected trading range, the opinion about the stock's near-term steadiness is likely to be fairly strongly held.

### Max Gain

- [[Source — Short Straddle]] · `Example` · lines 17–29
  > - Short 1 XYZ 60 call - Short 1 XYZ 60 put MAXIMUM GAIN - Premium received MAXIMUM LOSS - Unlimited
- [[Source — Short Straddle]] · `Max Gain` · lines 56–59
  > The maximum gain is limited to the premiums received at the outset. The best that can happen is for the stock price, at expiration, to be exactly at the strike price. In that case, both short options expire worthless, and the investor pockets the premium received for selling the options.

### Max Loss

- [[Source — Short Straddle]] · `Example` · lines 17–29
  > - Short 1 XYZ 60 call - Short 1 XYZ 60 put MAXIMUM GAIN - Premium received MAXIMUM LOSS - Unlimited
- [[Source — Short Straddle]] · `Max Loss` · lines 50–55
  > The maximum risk is unlimited. The worst that can happen is for the stock to rise to infinity, and the next-to-worst outcome is for the stock to fall to zero. In the first case, the loss is infinitely large; and in the second, the loss is the strike price. In either event, the loss is reduced by the amount of premium i

### Breakeven

- [[Source — Short Straddle]] · `Breakeven` · lines 66–73
  > This strategy breaks even if, at expiration, the stock price is either above or below the strike price by the total amount of premium income received. At either of those levels, one option's intrinsic value will equal the premium received for selling both options, while the other option will be expiring worthless. Upsi

### Volatility Effect

- [[Source — Short Straddle]] · `Volatility` · lines 74–79
  > Extremely important. This strategy's chances of success would be better if implied volatility were to fall. If the stock price holds steady and implied volatility falls quickly, the investor might conceivably be able to close out the position for a profit well before expiration. Conversely, if implied volatility rises

### Time Decay Effect

- [[Source — Short Straddle]] · `Time Decay` · lines 80–83
  > Extremely important positive effect. Every day that passes without a move in the underlying stock price brings both options one day closer to expiring, which would obviously be the investor's best-case scenario.

### Assignment Or Expiration Risk

- [[Source — Short Straddle]] · `Assignment Risk` · lines 84–89
  > Early assignment, while possible at any time, is more of a risk under certain circumstances: for a call, just before the stock goes ex-dividend; for a put, when it goes deep in-the-money. But the short straddle involves two short legs that could be assigned at any time during the life of the options, so investors shoul
- [[Source — Short Straddle]] · `Expiration Risk` · lines 90–95
  > The investor cannot know for sure whether or not they were assigned until the Monday after expiration. If the stock hovers just above and below the strike price on the day before expiration, it is even conceivable that both options might be assigned. The investor would have to prepare for several contingencies, includi

### Suitability Constraints

- [[Source — Short Straddle]] · `Motivation` · lines 40–43
  > Earn income from selling premium.
- [[Source — Short Straddle]] · `Comments` · lines 96–101
  > This strategy is really a race between volatility and time decay. Volatility is the storm which might blow in at any moment and cause extreme losses, or might not come at all. The passage of time brings the investor every day a little closer to realizing the expected profit. Note that this position is really a naked ca


See the [[index|Wiki Index]].
