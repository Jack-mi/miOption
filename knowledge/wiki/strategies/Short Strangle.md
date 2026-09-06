---
type: entity
title: Short Strangle
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - entity
  - strategy
  - strangle
entity_type: option-strategy
aliases:
  - short strangle
sources:
  - "[[Source — Short Strangle]]"
related: []
---

# Short Strangle

Collect premium with a wider profit zone than a short straddle, still exposed to large moves.

- Underlying: equity option
- Knowledge id: `strategy.short_strangle`
- Review status: `published`
- Futu category: 宽跨式策略 / Strangle

## Legs

- short out-of-the-money call (strike farther from the current stock price)
- short out-of-the-money put, same expiration

## Meaning

Collect premium with a wider profit zone than a short straddle, still exposed to large moves.

## Scenario

Neutral / range-bound with room between the short strikes; rising implied volatility hurts.

For short-premium traders who accept substantial risk outside the strikes and margin requirements.

## Method

- Maximum profit: The maximum gain is very limited. The maximum gain occurs if the underlying stock remains between the strike prices.
- Maximum loss: The maximum loss is unlimited. The maximum loss occurs if the stock goes to infinity, and a very substantial loss could occur if the stock became worthless.
- Break-even: This strategy breaks even if, at expiration, the stock price is either above the call strike price or below the put strike price by the amount of premium received initially. At either of those levels, one option's intrinsic value will equal the premium received for selling both options while the other option will be ex
- Assignment / expiration: Early assignment, while possible at any time, generally occurs for a call only when the stock goes ex-dividend or for a put when it goes deep in-the-money. And be aware, a situation where a stock is involved in a restructuring or capitalization event, such as a merger, takeover, spin-off or special dividend, could comp An investor cannot know for sure whether or not they will be assigned on either the call or put until the Monday after expiration. If an assignment occurs unexpectedly, they will find themselves long or short the stock on the Monday following expiration and subject to an adverse move in the stock over the weekend.

## How the price reacts to volatility and time

- Volatility: An increase in implied volatility, all other things equal, would have a very negative impact on this strategy. Even if the stock price holds steady, a quick rise in implied volatility would push up the value of both options and force the investor to put up additional margin in order to maintain the position.
- Time decay: The passage of time, all other things equal, will have a very positive impact on this strategy. Every day that passes without a move in the stock price brings both options one day closer to expiring worthless.

## Evidence

### Definition

- [[Source — Short Strangle]] · `Short Strangle` · lines 1–4
  > This strategy profits if the stock price and volatility remain steady during the life of the options.
- [[Source — Short Strangle]] · `Description` · lines 5–8
  > Selling a call and selling a put with the same expiration, but where the call strike price is above the put strike price is known as the short strangle strategy. Typically both options are out-of-the-money when the strategy is initiated.
- [[Source — Short Strangle]] · `Summary` · lines 13–16
  > This strategy tends to succeed if the stock price and volatility remain steady during the life of the options.

### Legs

- [[Source — Short Strangle]] · `Example` · lines 29–45
  > - Short 1 XYZ 65 call - Short 1 XYZ 55 put MAXIMUM GAIN - Net premium received MAXIMUM LOSS - Unlimited Strangles bring in less premium than straddles, but a larger move in the underlying stock is required before incurring a loss. Another variation of this strategy is the gut, where the call strike is below the put str

### Objective

- [[Source — Short Strangle]] · `Description` · lines 5–8
  > Selling a call and selling a put with the same expiration, but where the call strike price is above the put strike price is known as the short strangle strategy. Typically both options are out-of-the-money when the strategy is initiated.
- [[Source — Short Strangle]] · `Motivation` · lines 17–20
  > Earn income from selling premium.

### Market Outlook

- [[Source — Short Strangle]] · `Outlook` · lines 9–12
  > The investor is looking for a steady stock price during the life of the options.

### Max Gain

- [[Source — Short Strangle]] · `Example` · lines 29–45
  > - Short 1 XYZ 65 call - Short 1 XYZ 55 put MAXIMUM GAIN - Net premium received MAXIMUM LOSS - Unlimited Strangles bring in less premium than straddles, but a larger move in the underlying stock is required before incurring a loss. Another variation of this strategy is the gut, where the call strike is below the put str
- [[Source — Short Strangle]] · `Max Gain` · lines 50–53
  > The maximum gain is very limited. The maximum gain occurs if the underlying stock remains between the strike prices. In that case, both options expire worthless and the investor pockets the premium received for selling the options.

### Max Loss

- [[Source — Short Strangle]] · `Example` · lines 29–45
  > - Short 1 XYZ 65 call - Short 1 XYZ 55 put MAXIMUM GAIN - Net premium received MAXIMUM LOSS - Unlimited Strangles bring in less premium than straddles, but a larger move in the underlying stock is required before incurring a loss. Another variation of this strategy is the gut, where the call strike is below the put str
- [[Source — Short Strangle]] · `Max Loss` · lines 46–49
  > The maximum loss is unlimited. The maximum loss occurs if the stock goes to infinity, and a very substantial loss could occur if the stock became worthless. In both cases the loss is reduced by the amount of premium received for selling the options.

### Breakeven

- [[Source — Short Strangle]] · `Breakeven` · lines 58–65
  > This strategy breaks even if, at expiration, the stock price is either above the call strike price or below the put strike price by the amount of premium received initially. At either of those levels, one option's intrinsic value will equal the premium received for selling both options while the other option will be ex

### Volatility Effect

- [[Source — Short Strangle]] · `Volatility` · lines 66–69
  > An increase in implied volatility, all other things equal, would have a very negative impact on this strategy. Even if the stock price holds steady, a quick rise in implied volatility would push up the value of both options and force the investor to put up additional margin in order to maintain the position.

### Time Decay Effect

- [[Source — Short Strangle]] · `Time Decay` · lines 70–73
  > The passage of time, all other things equal, will have a very positive impact on this strategy. Every day that passes without a move in the stock price brings both options one day closer to expiring worthless.

### Assignment Or Expiration Risk

- [[Source — Short Strangle]] · `Assignment Risk` · lines 74–79
  > Early assignment, while possible at any time, generally occurs for a call only when the stock goes ex-dividend or for a put when it goes deep in-the-money. And be aware, a situation where a stock is involved in a restructuring or capitalization event, such as a merger, takeover, spin-off or special dividend, could comp
- [[Source — Short Strangle]] · `Expiration Risk` · lines 80–83
  > An investor cannot know for sure whether or not they will be assigned on either the call or put until the Monday after expiration. If an assignment occurs unexpectedly, they will find themselves long or short the stock on the Monday following expiration and subject to an adverse move in the stock over the weekend.

### Suitability Constraints

- [[Source — Short Strangle]] · `Motivation` · lines 17–20
  > Earn income from selling premium.
- [[Source — Short Strangle]] · `Comments` · lines 84–87
  > This strategy is really a race between volatility and time decay. Volatility is the storm which might blow in at any moment and cause extreme losses. The passage of time is a constant that brings the investor every day a little closer to realizing their anticipated profit.


See the [[index|Wiki Index]].
