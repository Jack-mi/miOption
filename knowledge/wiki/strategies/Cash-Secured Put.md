---
type: entity
title: Cash-Secured Put
status: evergreen
created: 2026-09-02
updated: 2026-09-02
tags:
  - entity
  - strategy
  - covered-stock
entity_type: option-strategy
aliases:
  - cash-secured put
  - cash secured put
sources:
  - "[[Source — Cash-Secured Put]]"
related:
  - "[[Naked Put (Uncovered Put, Short Put)]]"
---

# Cash-Secured Put

Acquire stock below the current market price via put assignment, while earning premium if the put expires unassigned.

- Underlying: equity stock
- Knowledge id: `strategy.cash_secured_put`
- Review status: `published`
- Futu category: 股票担保 / Covered Stock

## Legs

- short one put in the source example (put option)
- long cash equal to strike x 100 shares in the source example (cash / T-bill cover)

## Meaning

Acquire stock below the current market price via put assignment, while earning premium if the put expires unassigned.

## Scenario

Bullish longer term, looking for a short-term dip that may trigger assignment at an acceptable purchase price.

Only for investors who want to own the stock at the strike (less premium) and have set aside the cash to buy if assigned.

## Method

- Max gain: The maximum gain from the put option itself is limited. However, the optimal outcome is not readily apparent in the expiration profit/loss payoff diagram, because it does not address developments after expiration.
- Max loss: The maximum loss is limited but substantial. The worst that can happen is for the stock to become worthless.
- Breakeven: Since the object of this strategy is to acquire stock, the investor would break even if it is possible to sell the stock at the same effective price they paid for it. Breakeven = strike price – premium
- Assignment / expiration: Slight. Since the goal of this strategy is to acquire stock, assignment is not a problem. None. Since the goal of this strategy is to acquire stock, the investor should welcome an assignment at the option's expiration.

## Greeks and time

- Volatility: Whereas an increase in implied volatility would be considered an unqualified negative for a naked put writer, the effect could be described as neutral to slightly negative for the cash-secured put writer, all other things being equal. If it now appears likelier that the put will be assigned, greater volatility is a neu
- Time decay: The passage of time will have a positive impact on this strategy, all other things being equal. As expiration approaches, the option tends to move toward its intrinsic value, which for out-of-money puts is zero.

## Evidence

### Definition

- [[Source — Cash-Secured Put]] · `Cash-Secured Put` · lines 1–4
  > The cash-secured put involves writing a put option and simultaneously setting aside the cash to buy the stock if assigned.
- [[Source — Cash-Secured Put]] · `Description` · lines 5–16
  > The cash-secured put involves writing an at-the-money or out-of-the-money put option and simultaneously setting aside enough cash to buy the stock. The goal is to be assigned and acquire the stock below today's market price. Whether or not the put is assigned, all outcomes are presumably acceptable. The premium income
- [[Source — Cash-Secured Put]] · `Summary` · lines 36–41
  > The cash-secured put involves writing a put option and simultaneously setting aside the cash to buy the stock if assigned. If things go as hoped, it allows an investor to buy the stock at a price below its current market value. The investor must be prepared for the possibility that the put won't be assigned. In that ca

### Legs

- [[Source — Cash-Secured Put]] · `Example` · lines 17–31
  > - Short 1 XYZ 60 put - Long $6,000 T-Bill (cash that covers potential put assignment) MAXIMUM GAIN - Premium received MAXIMUM LOSS - Strike price - premium received (substantial) Second, by waiting for a price dip, the investor risks missing out on a stock that keeps climbing upward. The choices then include repeating

### Objective

- [[Source — Cash-Secured Put]] · `Description` · lines 5–16
  > The cash-secured put involves writing an at-the-money or out-of-the-money put option and simultaneously setting aside enough cash to buy the stock. The goal is to be assigned and acquire the stock below today's market price. Whether or not the put is assigned, all outcomes are presumably acceptable. The premium income
- [[Source — Cash-Secured Put]] · `Motivation` · lines 42–49
  > This is primarily a stock acquisition strategy for a price-sensitive investor. Unlike a naked put writer whose only goal is to collect premium income, a cash-secured put writer actually wants to acquire the underlying stock via assignment. The strike price, less the premium received, represents a desirable purchase pri

### Market Outlook

- [[Source — Cash-Secured Put]] · `Outlook` · lines 32–35
  > Looking for a short-term dip in stock price, followed by a longer-term appreciation.

### Max Gain

- [[Source — Cash-Secured Put]] · `Example` · lines 17–31
  > - Short 1 XYZ 60 put - Long $6,000 T-Bill (cash that covers potential put assignment) MAXIMUM GAIN - Premium received MAXIMUM LOSS - Strike price - premium received (substantial) Second, by waiting for a price dip, the investor risks missing out on a stock that keeps climbing upward. The choices then include repeating
- [[Source — Cash-Secured Put]] · `Max Gain` · lines 62–69
  > The maximum gain from the put option itself is limited. However, the optimal outcome is not readily apparent in the expiration profit/loss payoff diagram, because it does not address developments after expiration. The best scenario would be for the stock to dip slightly below the strike price at the put option's expira

### Max Loss

- [[Source — Cash-Secured Put]] · `Example` · lines 17–31
  > - Short 1 XYZ 60 put - Long $6,000 T-Bill (cash that covers potential put assignment) MAXIMUM GAIN - Premium received MAXIMUM LOSS - Strike price - premium received (substantial) Second, by waiting for a price dip, the investor risks missing out on a stock that keeps climbing upward. The choices then include repeating
- [[Source — Cash-Secured Put]] · `Max Loss` · lines 56–61
  > The maximum loss is limited but substantial. The worst that can happen is for the stock to become worthless. In that case, the investor would be obligated to buy stock at the strike price. The loss would be reduced by the premium received for selling the put option. Notice, however, that the maximum loss is lower than

### Breakeven

- [[Source — Cash-Secured Put]] · `Breakeven` · lines 80–85
  > Since the object of this strategy is to acquire stock, the investor would break even if it is possible to sell the stock at the same effective price they paid for it. Breakeven = strike price – premium

### Volatility Effect

- [[Source — Cash-Secured Put]] · `Volatility` · lines 86–93
  > Whereas an increase in implied volatility would be considered an unqualified negative for a naked put writer, the effect could be described as neutral to slightly negative for the cash-secured put writer, all other things being equal. If it now appears likelier that the put will be assigned, greater volatility is a neu

### Time Decay Effect

- [[Source — Cash-Secured Put]] · `Time Decay` · lines 94–97
  > The passage of time will have a positive impact on this strategy, all other things being equal. As expiration approaches, the option tends to move toward its intrinsic value, which for out-of-money puts is zero. If the original forecast and goals still apply, the investor keeps the premium and is free to either buy the

### Assignment Or Expiration Risk

- [[Source — Cash-Secured Put]] · `Assignment Risk` · lines 98–105
  > Slight. Since the goal of this strategy is to acquire stock, assignment is not a problem. However, early exercise would require the investor to convert the interest-bearing asset to cash in order to pay for the stock. Also, if assignment happened during a particularly severe downturn and the put writer has second thoug
- [[Source — Cash-Secured Put]] · `Expiration Risk` · lines 106–109
  > None. Since the goal of this strategy is to acquire stock, the investor should welcome an assignment at the option's expiration.

### Suitability Constraints

- [[Source — Cash-Secured Put]] · `Motivation` · lines 42–49
  > This is primarily a stock acquisition strategy for a price-sensitive investor. Unlike a naked put writer whose only goal is to collect premium income, a cash-secured put writer actually wants to acquire the underlying stock via assignment. The strike price, less the premium received, represents a desirable purchase pri
- [[Source — Cash-Secured Put]] · `Comments` · lines 110–117
  > Investors are told repeatedly to be wary of short option strategies, and quite rightly so. Without question, they entail tremendous risk, far greater than the limited premium income. They are definitely not suitable for all investors and situations. However, here is a short option strategy with a risk profile that is i

## See also

- related to: [[Naked Put (Uncovered Put, Short Put)]]

See the [[index|Wiki Index]].
