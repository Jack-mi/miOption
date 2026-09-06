---
type: entity
title: Protective Put (Married Put)
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - entity
  - strategy
  - single-option
entity_type: option-strategy
aliases:
  - protective put
  - married put
sources:
  - "[[Source — Protective Put (Married Put)]]"
related: []
---

# Protective Put (Married Put)

Floor the downside of a long stock position by paying a put premium for temporary protection.

- Underlying: equity stock
- Knowledge id: `strategy.protective_put`
- Review status: `published`
- Futu category: 单腿期权 / Single Option

## Legs

- long shares matching the put (underlying stock)
- long one put covering the stock (put option)

## Meaning

Floor the downside of a long stock position by paying a put premium for temporary protection.

## Scenario

Bullish or still holding stock, but wants insurance against a near-term decline.

For stock holders willing to pay premium for a known exit floor; not a profit-maximizing income strategy.

## Method

- Maximum profit: In theory, the potential gains on this strategy are unlimited. The best that can happen is for the stock price to rise to infinity.
- Maximum loss: The maximum loss is limited. The worst that can happen is for the stock to drop below the strike price.
- Break-even: There is no single formula to determine the strategy's breakeven point. Whether this strategy results in a profit or loss is largely determined by the purchase price of the stock, which may have occurred well in the past at a much lower price.
- Assignment / expiration: None. None, providing that the investor knows the pre-established minimum value for automatic exercise. If the protective put holder carries the open position into expiration, it indicates a desire to exercise the option if it's sufficiently in-the-money.

## How the price reacts to volatility and time

- Volatility: An increase in implied volatility would have a neutral to slightly positive impact on this strategy, all other things being equal. On one hand, the investor might perceive a greater value to having the put protection, since the market seems to think a big move has become likely.
- Time decay: The passage of time will have a negative impact on this strategy, all other things being equal. The protection of the hedge ends at expiration.

## Evidence

### Definition

- [[Source — Protective Put (Married Put)]] · `Protective Put (Married Put)` · lines 1–4
  > This strategy consists of adding a long put position to a long stock position.
- [[Source — Protective Put (Married Put)]] · `Description` · lines 5–16
  > A long put option added to long stock insures the stock's value. The choice of strike prices determines where the downside protection 'kicks in’. If the stock stays strong, the investor still gets the benefit of upside gains. (In fact, if the short-term forecast brightens before the put expires, it could be sold back t
- [[Source — Protective Put (Married Put)]] · `Summary` · lines 40–45
  > This strategy consists of adding a long put position to a long stock position. The protective put establishes a 'floor' price under which investor's stock value cannot fall. If the stock keeps rising, the investor benefits from the upside gains. Yet no matter how low the stock might fall, the investor can exercise the

### Legs

- [[Source — Protective Put (Married Put)]] · `Example` · lines 17–33
  > - Long 100 shares XYZ stock - Long 1 XYZ 60 put MAXIMUM GAIN - Unlimited MAXIMUM LOSS - Stock purchase price - strike price + premium paid If the investor remains nervous, the put could be held into expiration to extend the protection for as long as possible. Then it either expires worthless or, if it is sufficiently i

### Objective

- [[Source — Protective Put (Married Put)]] · `Description` · lines 5–16
  > A long put option added to long stock insures the stock's value. The choice of strike prices determines where the downside protection 'kicks in’. If the stock stays strong, the investor still gets the benefit of upside gains. (In fact, if the short-term forecast brightens before the put expires, it could be sold back t
- [[Source — Protective Put (Married Put)]] · `Motivation` · lines 46–57
  > This strategy is a hedge against a temporary dip in the stock's value. The protective put buyer retains the upside potential of the stock, while limiting the downside risk. Some examples of when investors consider protective puts: - Before an imminent news announcement that could send a favorite stock into a slump. - W

### Market Outlook

- [[Source — Protective Put (Married Put)]] · `Outlook` · lines 34–39
  > This investor is bullish overall, but worries about a sharp temporary decline in the underlying stock's price. If the investor is worried about the longer-term prospects also, other strategy choices might be a covered call or liquidating the stock and selecting another.

### Max Gain

- [[Source — Protective Put (Married Put)]] · `Example` · lines 17–33
  > - Long 100 shares XYZ stock - Long 1 XYZ 60 put MAXIMUM GAIN - Unlimited MAXIMUM LOSS - Stock purchase price - strike price + premium paid If the investor remains nervous, the put could be held into expiration to extend the protection for as long as possible. Then it either expires worthless or, if it is sufficiently i
- [[Source — Protective Put (Married Put)]] · `Max Gain` · lines 68–73
  > In theory, the potential gains on this strategy are unlimited. The best that can happen is for the stock price to rise to infinity. If the stock rises sharply, it does not matter that the put expires worthless. A protective put is analogous to homeowner's insurance. The asset is the primary concern, and to file a claim

### Max Loss

- [[Source — Protective Put (Married Put)]] · `Example` · lines 17–33
  > - Long 100 shares XYZ stock - Long 1 XYZ 60 put MAXIMUM GAIN - Unlimited MAXIMUM LOSS - Stock purchase price - strike price + premium paid If the investor remains nervous, the put could be held into expiration to extend the protection for as long as possible. Then it either expires worthless or, if it is sufficiently i
- [[Source — Protective Put (Married Put)]] · `Max Loss` · lines 62–67
  > The maximum loss is limited. The worst that can happen is for the stock to drop below the strike price. It does not matter how far below; the put caps the loss at that point. The strike becomes the 'floor' exit price at which the investor can liquidate the stock, regardless of how low the market price might fall. The a

### Breakeven

- [[Source — Protective Put (Married Put)]] · `Breakeven` · lines 84–91
  > There is no single formula to determine the strategy's breakeven point. Whether this strategy results in a profit or loss is largely determined by the purchase price of the stock, which may have occurred well in the past at a much lower price. Assume the stock was acquired at or just below its current price. If the unr

### Volatility Effect

- [[Source — Protective Put (Married Put)]] · `Volatility` · lines 92–97
  > An increase in implied volatility would have a neutral to slightly positive impact on this strategy, all other things being equal. On one hand, the investor might perceive a greater value to having the put protection, since the market seems to think a big move has become likely. But even if the investor disagrees with

### Time Decay Effect

- [[Source — Protective Put (Married Put)]] · `Time Decay` · lines 98–101
  > The passage of time will have a negative impact on this strategy, all other things being equal. The protection of the hedge ends at expiration. As for the put's resale value in the market, the option tends to move toward its intrinsic value as the term draws to an end. For at-the-money and out-of-money puts, intrinsic

### Assignment Or Expiration Risk

- [[Source — Protective Put (Married Put)]] · `Assignment Risk` · lines 102–105
  > None.
- [[Source — Protective Put (Married Put)]] · `Expiration Risk` · lines 106–109
  > None, providing that the investor knows the pre-established minimum value for automatic exercise. If the protective put holder carries the open position into expiration, it indicates a desire to exercise the option if it's sufficiently in-the-money. Investors with no intention of exiting their stock position may need t

### Suitability Constraints

- [[Source — Protective Put (Married Put)]] · `Motivation` · lines 46–57
  > This strategy is a hedge against a temporary dip in the stock's value. The protective put buyer retains the upside potential of the stock, while limiting the downside risk. Some examples of when investors consider protective puts: - Before an imminent news announcement that could send a favorite stock into a slump. - W
- [[Source — Protective Put (Married Put)]] · `Comments` · lines 110–113
  > A note to investors who are considering protective puts because they cannot liquidate the stock right away but are nervous about its prospects: it's important to make sure that a put hedge is the right solution from all standpoints, including law and taxes. For example, if employment-related stock sale restrictions app


See the [[index|Wiki Index]].
