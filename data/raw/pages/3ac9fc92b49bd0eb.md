# Short Straddle

This strategy involves selling a call option and a put option with the same expiration and strike price.

### Description

A short straddle is a combination of writing uncovered calls (bearish) and writing uncovered puts (bullish), both with the same strike price and expiration. Together, they produce a position that predicts a narrow trading range for the underlying stock.

Before there were options, it was difficult for investors to profit directly from an accurate prediction that didn't involve a steep rise or fall in the stock. The short straddle is an example of a strategy that does. By collecting two up-front premiums initially, the investor builds a larger margin of error, compared to writing just a call or a put option. However, the risks are substantial on the downside and unlimited on the upside, should a large move occur.

The investor may be able to reduce the chance of assignment by selecting a longer term to expiration, and by monitoring the underlying stock closely and being ready to take quick action. Still no precaution can change the fundamentals: limited rewards for unlimited risk.

![Short Straddle P&L chart; Short call & put at 60 (green dot); Max profit at 60, Unlimited loss both directions](https://www.optionseducation.org/getmedia/d2deb6b2-cd36-4187-97d8-440237cda1dd/Short-Straddle_PnL.png?width=260&height=260 "Short Straddle P&L chart; Short call & put at 60 (green dot); Max profit at 60, Unlimited loss both directions")

Net Position (at expiration)

### Example

*   Short 1 XYZ 60 call
*   Short 1 XYZ 60 put

**MAXIMUM GAIN**

*   Premium received

**MAXIMUM LOSS**

*   Unlimited

### Outlook

The strategy hopes for a steady stock price during the life of the options, and an even or declining level of implied volatility.

Because of the substantial risk, should the stock price move out of the expected trading range, the opinion about the stock's near-term steadiness is likely to be fairly strongly held.

### Summary

This strategy involves selling a call option and a put option with the same expiration and strike price. It generally profits if the stock price and volatility remain steady.

### Motivation

Earn income from selling premium.

### Variations

A short straddle assumes that the call and put options both have the same strike price. See the discussion under [short strangle](https://www.optionseducation.org/strategies/all-strategies/short-strangle) for a variation on the same strategy, but with a higher call strike and a lower put strike.

In yet another application, a cautious but still bullish stockowner could reduce an existing long stock position and simultaneously write an at-the-money short straddle, a strategy known as a protective straddle or covered straddle. For a longer discussion of this concept, refer to [covered strangle](https://www.optionseducation.org/strategies/all-strategies/covered-strangle-covered-combination).

### Max Loss

The maximum risk is unlimited. The worst that can happen is for the stock to rise to infinity, and the next-to-worst outcome is for the stock to fall to zero. In the first case, the loss is infinitely large; and in the second, the loss is the strike price. In either event, the loss is reduced by the amount of premium income received for selling the options.

If the stock price is higher than the call strike, the investor will be assigned and therefore obligated to sell stock at the strike price and buy it in the market. If the stock price is lower than the put strike, the investor will be assigned and therefore be obligated to buy stock at the strike price, regardless of the lower market value. That means either liquidating it in the market for an immediate loss, or keeping a stock that cost more than its current market value.

### Max Gain

The maximum gain is limited to the premiums received at the outset. The best that can happen is for the stock price, at expiration, to be exactly at the strike price. In that case, both short options expire worthless, and the investor pockets the premium received for selling the options.

### Profit/Loss

The potential profit is extremely limited. In the best-case scenario, the short positions are held into expiration and the stock closes exactly at the strike price, and both options expire without being assigned. The investor then keeps the premiums for both the calls and puts.

Any other outcome involves being assigned, or being driven to cover, one or both parts of the straddle. Depending on the stock price, the net result will be either a lesser profit or a loss. The 'double' premiums received at the outset offer some margin for error should the stock move in either direction, but the potential for huge losses remains.

### Breakeven

This strategy breaks even if, at expiration, the stock price is either above or below the strike price by the total amount of premium income received. At either of those levels, one option's intrinsic value will equal the premium received for selling both options, while the other option will be expiring worthless.

Upside breakeven = strike + premiums received

Downside breakeven = strike - premiums received

### Volatility

Extremely important. This strategy's chances of success would be better if implied volatility were to fall. If the stock price holds steady and implied volatility falls quickly, the investor might conceivably be able to close out the position for a profit well before expiration.

Conversely, if implied volatility rises unexpectedly, the effect on this strategy is very negative. The possibility of the underlying moving beyond the breakeven point seems likelier (at least in the market's opinion), and consequently the cost of closing out the straddle escalates as well. It could force the investor to close out at a loss, if only to prevent further losses.

### Time Decay

Extremely important positive effect. Every day that passes without a move in the underlying stock price brings both options one day closer to expiring, which would obviously be the investor's best-case scenario.

### Assignment Risk

Early assignment, while possible at any time, is more of a risk under certain circumstances: for a call, just before the stock goes ex-dividend; for a put, when it goes deep in-the-money. But the short straddle involves two short legs that could be assigned at any time during the life of the options, so investors should be monitoring the likelihood of assignment.

And be aware, a situation where a stock is involved in a restructuring or capitalization event, such as a merger, takeover, spin-off or special dividend, could completely upset typical expectations regarding early exercise of options on the stock.

### Expiration Risk

The investor cannot know for sure whether or not they were assigned until the Monday after expiration. If the stock hovers just above and below the strike price on the day before expiration, it is even conceivable that both options might be assigned. The investor would have to prepare for several contingencies, including being assigned on one option, the other option, both, or neither. There is no sure way to 'cover' for all outcomes, and guessing wrong could result in an unexpected long or short stock position on the following Monday, subject to an adverse move in the stock over the weekend.

Close monitoring and setting aside the resources to handle all outcomes are one way to prepare for this risk; closing the straddle out early is the other way.

### Comments

This strategy is really a race between volatility and time decay. Volatility is the storm which might blow in at any moment and cause extreme losses, or might not come at all. The passage of time brings the investor every day a little closer to realizing the expected profit.

Note that this position is really a [naked call](https://www.optionseducation.org/strategies/all-strategies/naked-call-uncovered-call-short-call) and [naked put](https://www.optionseducation.org/strategies/all-strategies/naked-put-uncovered-put-short-put) combined.

### Related Position

Comparable Position: N/A

Opposite Position: [Long Straddle](https://www.optionseducation.org/strategies/all-strategies/long-straddle)