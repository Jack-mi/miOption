---
type: entity
title: Collar (Protective Collar)
status: evergreen
created: 2026-09-02
updated: 2026-09-03
tags:
  - entity
  - strategy
  - collar
entity_type: option-strategy
aliases:
  - collar
  - protective collar
sources:
  - "[[Source — Collar Protective Collar - Options Education]]"
related: []
---

# Collar (Protective Collar)

Temporarily hedge a long stock holding between a put floor and a call ceiling, often at low net premium.

- Underlying: equity stock
- Knowledge id: `strategy.collar`
- Review status: `published`
- Futu category: 领口策略 / Collar

## Legs

- long shares being collared (underlying stock)
- long lower-strike put (floor) (put option)
- short higher-strike call (ceiling), same expiration (call option)

## Meaning

Temporarily hedge a long stock holding between a put floor and a call ceiling, often at low net premium.

## Scenario

Wants near-term protection on stock already held; accepts capped upside while the collar is on.

For stock holders seeking a temporary hedge who accept selling shares at the call strike if assigned.

## Method

- Maximum profit: The maximum gain is limited for the term of the strategy. The short-term maximum gains are reached just as the stock price rises to the call strike.
- Maximum loss: The maximum loss is limited for the term of the collar hedge. The worst that can happen is for the stock price to fall below the put strike, which prompts the investor to exercise the put and sell the stock at the 'floor' price: the put strike.
- Break-even: In principle, the strategy breaks even if, at expiration, the stock is above (below) its initial level by the amount of the debit (credit). If the stock is a long-term holding purchased at a much lower price, the concept of breakeven isn't relevant.
- Assignment / expiration: Yes. Early assignment of the short call option, while possible at any time, generally occurs only just before the stock goes ex-dividend. The option writer cannot know for sure whether or not assignment actually occurred on the short call until the following Monday. However, this is generally not an issue since the investor has stock to deliver if assigned on the call.

## How the price reacts to volatility and time

- Volatility: Volatility is usually not a major consideration in this strategy, all things being equal. Since the strategy involves being long one option and short another with the same expiration (and generally equidistant from the stock value), the effects of implied volatility shifts may offset each other to a large degree.
- Time decay: Usually not a major consideration. Since the strategy involves being long one option and short another with the same expiration (and generally equidistant from the stock value), the effects of time decay should roughly offset each other.

## Evidence

### Definition

- [[Source — Collar Protective Collar - Options Education]] · `Collar Protective Collar | Options Education` · lines 1–4
  > The investor adds a collar to an existing long stock position as a temporary, slightly less-than-complete hedge against the effects of a possible near-term decline.
- [[Source — Collar Protective Collar - Options Education]] · `Description` · lines 5–16
  > An investor writes a call option and buys a put option with the same expiration as a means to hedge a long position in the underlying stock. This strategy combines two other hedging strategies: protective puts and covered call writing. Usually, the investor will select a call strike above and a long put strike below th
- [[Source — Collar Protective Collar - Options Education]] · `Summary` · lines 39–42
  > The investor adds a collar to an existing long stock position as a temporary, slightly less-than-complete hedge against the effects of a possible near-term decline. The long put strike provides a minimum selling price for the stock, and the short call strike sets a maximum profit price. To protect or collar a short sto

### Legs

- [[Source — Collar Protective Collar - Options Education]] · `Example` · lines 25–38
  > - Long 100 shares XYZ stock - Short 1 XYZ 65 call - Long 1 XYZ 55 put MAXIMUM GAIN - Call strike - stock purchase price - net premium paid OR Call strike - stock purchase price + net credit received MAXIMUM LOSS - Stock purchase price - put strike - net premium paid OR Stock purchase - put strike + net credit received

### Objective

- [[Source — Collar Protective Collar - Options Education]] · `Description` · lines 5–16
  > An investor writes a call option and buys a put option with the same expiration as a means to hedge a long position in the underlying stock. This strategy combines two other hedging strategies: protective puts and covered call writing. Usually, the investor will select a call strike above and a long put strike below th
- [[Source — Collar Protective Collar - Options Education]] · `Motivation` · lines 43–46
  > This strategy is for holders or buyers of a stock who are concerned about a correction and wish to hedge the long stock position.

### Market Outlook

- [[Source — Collar Protective Collar - Options Education]] · `Outlook` · lines 17–24
  > For the term of the option strategy, the investor is looking for a slight rise in the stock price, but is worried about a decline. Net Position (at expiration)

### Max Gain

- [[Source — Collar Protective Collar - Options Education]] · `Example` · lines 25–38
  > - Long 100 shares XYZ stock - Short 1 XYZ 65 call - Long 1 XYZ 55 put MAXIMUM GAIN - Call strike - stock purchase price - net premium paid OR Call strike - stock purchase price + net credit received MAXIMUM LOSS - Stock purchase price - put strike - net premium paid OR Stock purchase - put strike + net credit received
- [[Source — Collar Protective Collar - Options Education]] · `Max Gain` · lines 57–64
  > The maximum gain is limited for the term of the strategy. The short-term maximum gains are reached just as the stock price rises to the call strike. The net profit remains the same no matter how much higher the stock might close; only the position outcome might differ. If the stock is above the call strike at expiratio

### Max Loss

- [[Source — Collar Protective Collar - Options Education]] · `Example` · lines 25–38
  > - Long 100 shares XYZ stock - Short 1 XYZ 65 call - Long 1 XYZ 55 put MAXIMUM GAIN - Call strike - stock purchase price - net premium paid OR Call strike - stock purchase price + net credit received MAXIMUM LOSS - Stock purchase price - put strike - net premium paid OR Stock purchase - put strike + net credit received
- [[Source — Collar Protective Collar - Options Education]] · `Max Loss` · lines 51–56
  > The maximum loss is limited for the term of the collar hedge. The worst that can happen is for the stock price to fall below the put strike, which prompts the investor to exercise the put and sell the stock at the 'floor' price: the put strike. If the stock had originally been bought at a much lower price (which is oft

### Breakeven

- [[Source — Collar Protective Collar - Options Education]] · `Breakeven` · lines 71–74
  > In principle, the strategy breaks even if, at expiration, the stock is above (below) its initial level by the amount of the debit (credit). If the stock is a long-term holding purchased at a much lower price, the concept of breakeven isn't relevant.

### Volatility Effect

- [[Source — Collar Protective Collar - Options Education]] · `Volatility` · lines 75–78
  > Volatility is usually not a major consideration in this strategy, all things being equal. Since the strategy involves being long one option and short another with the same expiration (and generally equidistant from the stock value), the effects of implied volatility shifts may offset each other to a large degree.

### Time Decay Effect

- [[Source — Collar Protective Collar - Options Education]] · `Time Decay` · lines 79–82
  > Usually not a major consideration. Since the strategy involves being long one option and short another with the same expiration (and generally equidistant from the stock value), the effects of time decay should roughly offset each other.

### Assignment Or Expiration Risk

- [[Source — Collar Protective Collar - Options Education]] · `Assignment Risk` · lines 83–88
  > Yes. Early assignment of the short call option, while possible at any time, generally occurs only just before the stock goes ex-dividend. And be aware, a situation where a stock is involved in a restructuring or capitalization event, such as for example a merger, takeover, spin-off or special dividend, could completely
- [[Source — Collar Protective Collar - Options Education]] · `Expiration Risk` · lines 89–92
  > The option writer cannot know for sure whether or not assignment actually occurred on the short call until the following Monday. However, this is generally not an issue since the investor has stock to deliver if assigned on the call.

### Suitability Constraints

- [[Source — Collar Protective Collar - Options Education]] · `Motivation` · lines 43–46
  > This strategy is for holders or buyers of a stock who are concerned about a correction and wish to hedge the long stock position.
- [[Source — Collar Protective Collar - Options Education]] · `Comments` · lines 93–96
  > This strategy lends itself to use as a LEAPS® hedge, where time value tends to make premiums higher and the period of protection is longer. The collar offers more protection than a covered call, but at a lower up-front cost than a protective put. See both of these alternatives for additional details.


See the [[index|Wiki Index]].
