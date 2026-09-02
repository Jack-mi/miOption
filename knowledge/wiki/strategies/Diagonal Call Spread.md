---
type: entity
title: Diagonal Call Spread
status: evergreen
created: 2026-09-02
updated: 2026-09-02
tags:
  - entity
  - strategy
  - diagonal-spread
entity_type: option-strategy
aliases:
  - diagonal spread
  - call diagonal
sources:
  - "[[Source — Wikipedia Diagonal spread]]"
  - "[[Source — Long Call Calendar Spread (Call Horizontal)]]"
related:
  - "[[Long Call Calendar Spread]]"
  - "[[Long Put Calendar Spread]]"
---

# Diagonal Call Spread

Buy and sell the same type of option (calls or puts) with **different strikes and different expirations**. Combines a calendar and a vertical. Futu's 对角 menu maps here.

- Underlying: equity option
- Knowledge id: `strategy.diagonal_spread`
- Review status: `published`
- Futu category: 对角策略 / Diagonal Spread

Wikipedia is the dedicated structure source. It does **not** publish one max-gain / max-loss / breakeven formula: too many strike and expiry combinations. Calendar-page numbers are not copied here.

## Legs

Typical one-to-one long diagonal:

- short near-term option at one strike
- long longer-dated option of the same type at a different strike

Wikipedia also allows ratioed (unequal) counts. Puts follow the same structure as calls.

## Meaning

A diagonal spread shares features of both a calendar spread and a vertical spread. It is established by simultaneously buying and selling equal amount of option contracts of the same type (calls or puts) but with different strike prices and expiration dates.

OIC: a calendar most commonly uses the same strike (horizontal); different strikes make it a diagonal, with a slightly different profit/loss profile.

## Scenario

Strike choice tilts bullish or bearish versus a same-strike calendar. A one-to-one diagonal with similar deltas behaves much like a calendar: close to delta-neutral, P/L driven mainly by volatility and time, not direction.

## Method

- Max gain: Not a single published number. Wikipedia: each diagonal must be analyzed individually for its risk and reward profile.
- Max loss: Not a single published number. Same reason.
- Breakeven: Not a single published number. Same reason.
- Assignment / expiration: The short near-term option can be assigned. For a short call, OIC calendar assignment text still applies to that short call leg (early assignment generally when the stock goes ex-dividend).

## Greeks and time

- Volatility / time: Wikipedia: when constructed one-to-one with similar deltas, profit or loss is driven mainly by changes in volatility and the passage of time.
- Do not treat same-strike calendar max-gain/max-loss formulas as the diagonal's published P/L.

## Evidence

### Definition

- [[Source — Wikipedia Diagonal spread]] · `Diagonal spread` · lines 5–6
  > In derivatives trading, the term diagonal spread is applied to an options spread position that shares features of both a calendar spread and a vertical spread. It is established by simultaneously buying and selling equal amount of option contracts of the same type (call options or put options) but with different strike prices and expiration dates.
- [[Source — Wikipedia Diagonal spread]] · `Difference from calendar and vertical` · lines 8–10
  > A diagonal spread differs from a pure calendar spread in that the strike prices are not the same, and from a pure vertical spread in that the expiration dates are not the same. Many diagonal spreads are constructed one-to-one (one long-term option for each short-term option), but they can also be created with unequal numbers of long and short market contracts (ratioed spreads). Due to the large number of possible variations, each diagonal spread must be analyzed individually to determine its risk and reward profile.
- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Description`
  > The strategy most commonly involves calls with the same strike (horizontal spread), but can also be done with different strikes (diagonal spread).
- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Variations`
  > A diagonal spread, involving two calls with different strikes as well as expirations, would have a slightly different profit/loss profile. The basic concepts, however, would continue to apply.

### Legs

- [[Source — Wikipedia Diagonal spread]] · `Example` · lines 16–25
  > Buy 1 June 115 call / Sell 1 April 110 call (and a matching put pair in the same example). Expirations differ and strikes differ within each pair.

### Market Outlook

- [[Source — Wikipedia Diagonal spread]] · `One-to-one similar-delta case` · lines 12–14
  > When a diagonal spread is constructed one-to-one, with both options having approximately the same delta, it behaves much like a conventional calendar spread. In this case, the position tends to be close to delta-neutral, with its profit or loss driven mainly by changes in volatility and the passage of time, rather than directional movement of the underlying.

### Assignment Or Expiration Risk

- [[Source — Long Call Calendar Spread (Call Horizontal)]] · `Assignment Risk`
  > Yes. Early assignment, while possible at any time, generally occurs for a call only when the stock goes ex-dividend.

## See also

- related to: [[Long Call Calendar Spread]]
- related to: [[Long Put Calendar Spread]]

See the [[index|Wiki Index]].
