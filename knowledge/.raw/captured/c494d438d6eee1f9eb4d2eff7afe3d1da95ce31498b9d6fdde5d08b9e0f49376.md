# Long Strangle (Long Combination)

This strategy profits if the stock price moves sharply in either direction during the life of the option.

### Description

This strategy typically involves buying an out-of-the money call option and an out-of-the-money put option with the same expiration date.

### Outlook

The investor is looking for a sharp move in the underlying stock, either up or down, during the life of the options.

### Summary

This strategy does best if the stock price moves sharply in either direction during the life of the options.

### Motivation

The strategy hopes to capture a quick increase in implied volatility or a big move in the underlying stock price during the life of the options.

![Long Strangle P&L chart; Max loss between 55-65 (red dots); Profit increases below 50 and above 70](https://www.optionseducation.org/getmedia/be3c1675-ea16-4ed8-b5a4-a392d9157d12/Long-Strangle-PnL.png?width=260&height=260 "Long Strangle P&L chart; Max loss between 55-65 (red dots); Profit increases below 50 and above 70")

Net Position (at expiration)

### Example

*   Long 1 XYZ 65 call
*   Long 1 XYZ 55 put

**MAXIMUM GAIN**

*   Unlimited

**MAXIMUM LOSS**

*   Net premium paid

### Variations

This strategy differs from a [straddle](https://www.optionseducation.org/strategies/all-strategies/long-straddle) in that the call strike is above the put strike. As a general rule, both the call and the put are out-of-the-money. Strangles are less expensive than straddles, but a larger move in the underlying stock is generally required to reach breakeven.

Another variation of this strategy is the gut, where the call strike is below the put strike. Because both the call and put strike prices of a gut are usually in-the-money, at least one of them has to be, this strategy is very expensive and therefore rarely used.

### Max Loss

The maximum loss is limited. The maximum loss occurs if the underlying stock remains between the strike prices until expiration. If at expiration the stock's price is between the strikes, both options will expire worthless and the entire premium paid will have been lost.

### Max Gain

The maximum gain is unlimited. The maximum gain occurs if the underlying stock goes to infinity, and a very substantial gain would occur if the stock became worthless. The gross profit at expiration would be the difference between the stock's price and either the call strike price if the stock price is higher or the put strike price if the stock price is lower. The net profit is the gross profit less the premium paid for the options. There is no limit to the upside potential and the downside potential is limited only because the stock price cannot go below zero.

### Profit/Loss

The potential profit is unlimited on the upside and very substantial on the downside. The loss is limited to the premium paid for the options.

### Breakeven

This strategy breaks even if, at expiration, the stock price is either above the call strike price or below the put strike price by the amount of premium paid. At either of those levels, one option's intrinsic value will equal the premium paid for both options while the other option will be expiring worthless.

Upside breakeven = call strike + premiums paid

Downside breakeven = put strike - premiums paid

### Volatility

An increase in implied volatility, all other things equal, would have a very positive impact on this strategy. Even if the stock price holds steady, a quick rise in implied volatility would push up the value of both options and might allow the investor to close out the position for a profit well before expiration.

### Time Decay

The passage of time, all other things equal, will have a very negative impact on this strategy. Because the strategy consists of being long two options, every day that passes without a move in the stock's price will cause their value to suffer a significant erosion of value.

### Assignment Risk

None.  The investor is in control.

### Expiration Risk

If the options are held into expiration, one of them may be subject to auto-exercise.

### Comments

This strategy is really a race between time decay and volatility. The passage of time is a constant that erodes the position's value a little bit every day. Volatility is the storm which might blow in at any moment, or which might never occur at all.

### Related Position

Comparable Position: N/A

Opposite Position: [Short Strangle](https://www.optionseducation.org/strategies/all-strategies/short-strangle)