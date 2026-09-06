---
type: entity
title: Bull Call Spread (Debit Call Spread)
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - entity
  - strategy
  - vertical-spread
entity_type: option-strategy
aliases:
  - bull call spread
  - debit call spread
  - vertical call debit
sources:
  - "[[Source — Bull Call Spread (Debit Call Spread)]]"
related: []
---

# Bull Call Spread (Debit Call Spread)

Express a moderately bullish view with defined risk and defined reward by financing a long call with a short higher call.

- Underlying: equity option
- Knowledge id: `strategy.bull_call_spread`
- Review status: `published`
- Futu category: 垂直策略 / Vertical Spread

## Legs

- long lower-strike call (call option)
- short higher-strike call, same expiration (call option)

## Meaning

Express a moderately bullish view with defined risk and defined reward by financing a long call with a short higher call.

## Scenario

Moderately bullish; expects a rise toward or above the short call strike by expiration.

For bullish investors who want lower cost and capped upside versus a naked long call.

## Method

- Maximum profit: The maximum gain is capped at expiration, should the stock price do even better than hoped and exceed the higher strike price. If the stock price is at or above the higher (short call) strike at expiration, in theory, the investor would exercise the long call component and presumably would be assigned on the short call
- Maximum loss: The maximum loss is very limited. The worst that can happen is for the stock to be below the lower strike price at expiration.
- Break-even: This strategy breaks even at expiration if the stock price is above the lower strike by the amount of the initial outlay (the debit). In that case, the short call would expire worthless and the long call's intrinsic value would equal the debit.
- Assignment / expiration: Early assignment, while possible at any time, generally occurs only when the stock goes ex-dividend. Be warned, however, that using the long call to cover the short call assignment will require establishing a short stock position for one business day, due to the delay in assignment notification. Yes. If held into expiration this strategy entails added risk.

## How the price reacts to volatility and time

- Volatility: Slight, all other things being equal. Since the strategy involves being long one call and short another with the same expiration, the effects of volatility shifts on the two contracts may offset each other to a large degree.
- Time decay: The passage of time hurts the position, though not as much as it does a plain long call position. Since the strategy involves being long one call and short another with the same expiration, the effects of time decay on the two contracts may offset each other to a large degree.

## Evidence

### Definition

- [[Source — Bull Call Spread (Debit Call Spread)]] · `Bull Call Spread (Debit Call Spread)` · lines 1–4
  > This strategy consists of buying one call option and selling another at a higher strike price to help pay the cost.
- [[Source — Bull Call Spread (Debit Call Spread)]] · `Description` · lines 5–16
  > A bull call spread is a type of vertical spread. It contains two calls with the same expiration but different strikes. The strike price of the short call is higher than the strike of the long call, which means this strategy will always require an initial outlay (debit). The short call's main purpose is to help pay for
- [[Source — Bull Call Spread (Debit Call Spread)]] · `Summary` · lines 38–41
  > This strategy consists of buying one call option and selling another at a higher strike price to help pay the cost. The spread generally profits if the stock price moves higher, just as a regular long call strategy would, up to the point where the short call caps further gains.

### Legs

- [[Source — Bull Call Spread (Debit Call Spread)]] · `Example` · lines 17–33
  > - Long 1 XYZ 60 call - Short 1 XYZ 65 call MAXIMUM GAIN - High strike - low strike - net premium paid MAXIMUM LOSS - Net premium paid The benefit of a higher short call strike is a higher maximum to the strategy's potential profit. The disadvantage is that the premium received is smaller, the higher the short call's st

### Objective

- [[Source — Bull Call Spread (Debit Call Spread)]] · `Description` · lines 5–16
  > A bull call spread is a type of vertical spread. It contains two calls with the same expiration but different strikes. The strike price of the short call is higher than the strike of the long call, which means this strategy will always require an initial outlay (debit). The short call's main purpose is to help pay for
- [[Source — Bull Call Spread (Debit Call Spread)]] · `Motivation` · lines 42–45
  > Profit from a gain in the underlying stock's price without the up-front capital outlay and downside risk of outright stock ownership.

### Market Outlook

- [[Source — Bull Call Spread (Debit Call Spread)]] · `Outlook` · lines 34–37
  > Looking for a steady or rising stock price during the life of the options. As with any limited-time strategy, the investor's long-term forecast for the underlying stock isn't as important, but this is probably not a suitable choice for those who have a bullish outlook past the immediate future. It would require an accu

### Max Gain

- [[Source — Bull Call Spread (Debit Call Spread)]] · `Example` · lines 17–33
  > - Long 1 XYZ 60 call - Short 1 XYZ 65 call MAXIMUM GAIN - High strike - low strike - net premium paid MAXIMUM LOSS - Net premium paid The benefit of a higher short call strike is a higher maximum to the strategy's potential profit. The disadvantage is that the premium received is smaller, the higher the short call's st
- [[Source — Bull Call Spread (Debit Call Spread)]] · `Max Gain` · lines 54–57
  > The maximum gain is capped at expiration, should the stock price do even better than hoped and exceed the higher strike price. If the stock price is at or above the higher (short call) strike at expiration, in theory, the investor would exercise the long call component and presumably would be assigned on the short call

### Max Loss

- [[Source — Bull Call Spread (Debit Call Spread)]] · `Example` · lines 17–33
  > - Long 1 XYZ 60 call - Short 1 XYZ 65 call MAXIMUM GAIN - High strike - low strike - net premium paid MAXIMUM LOSS - Net premium paid The benefit of a higher short call strike is a higher maximum to the strategy's potential profit. The disadvantage is that the premium received is smaller, the higher the short call's st
- [[Source — Bull Call Spread (Debit Call Spread)]] · `Max Loss` · lines 50–53
  > The maximum loss is very limited. The worst that can happen is for the stock to be below the lower strike price at expiration. In that case, both call options expire worthless, and the loss incurred is simply the initial outlay for the position (the net debit).

### Breakeven

- [[Source — Bull Call Spread (Debit Call Spread)]] · `Breakeven` · lines 62–67
  > This strategy breaks even at expiration if the stock price is above the lower strike by the amount of the initial outlay (the debit). In that case, the short call would expire worthless and the long call's intrinsic value would equal the debit. Breakeven = long call strike + net debit paid

### Volatility Effect

- [[Source — Bull Call Spread (Debit Call Spread)]] · `Volatility` · lines 68–73
  > Slight, all other things being equal. Since the strategy involves being long one call and short another with the same expiration, the effects of volatility shifts on the two contracts may offset each other to a large degree. Note, however, that the stock price can move in such a way that a volatility change would affec

### Time Decay Effect

- [[Source — Bull Call Spread (Debit Call Spread)]] · `Time Decay` · lines 74–79
  > The passage of time hurts the position, though not as much as it does a plain long call position. Since the strategy involves being long one call and short another with the same expiration, the effects of time decay on the two contracts may offset each other to a large degree. Regardless of the theoretical price impact

### Assignment Or Expiration Risk

- [[Source — Bull Call Spread (Debit Call Spread)]] · `Assignment Risk` · lines 80–85
  > Early assignment, while possible at any time, generally occurs only when the stock goes ex-dividend. Be warned, however, that using the long call to cover the short call assignment will require establishing a short stock position for one business day, due to the delay in assignment notification. And be aware, any situa
- [[Source — Bull Call Spread (Debit Call Spread)]] · `Expiration Risk` · lines 86–93
  > Yes. If held into expiration this strategy entails added risk. The investor cannot know for sure until the following Monday whether or not the short call was assigned. The problem is most acute if the stock is trading just below, at or just above the short call strike. Assume that the long call is in-the-money and that

### Suitability Constraints

- [[Source — Bull Call Spread (Debit Call Spread)]] · `Motivation` · lines 42–45
  > Profit from a gain in the underlying stock's price without the up-front capital outlay and downside risk of outright stock ownership.


See the [[index|Wiki Index]].
