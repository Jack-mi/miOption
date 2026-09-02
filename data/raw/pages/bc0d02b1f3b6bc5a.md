# Short Condor (Iron Condor)

This strategy profits if the underlying stock is inside the inner wings at expiration.

### Description

To construct a short condor, the investor sells one call while buying another call with a higher strike and sells one put while buying another put with a lower strike. Typically, the call strikes are above and the put strikes below the current level of underlying stock, and the distance between the call strikes equals the distance between the put strikes. All the options must be of the same expiration.

An alternative way to think about this strategy is as a [short strangle](https://www.optionseducation.org/strategies/all-strategies/short-strangle) and long an even wider strangle. It could also be considered as a [bear call spread](https://www.optionseducation.org/strategies/all-strategies/bear-call-spread-credit-call-spread) and a [bull put spread](https://www.optionseducation.org/strategies/all-strategies/bull-put-spread-credit-put-spread).

### Outlook

The investor is hoping for underlying stock to trade in narrow range during the life of the options.

### Summary

This strategy profits if the underlying stock is inside the inner wings at expiration.

![Short Condor P&L chart; Short 55 put & 65 call (green dots), Long 50 put & 70 call (red dots); Max loss between 55-65, Max profit below 50 or above 70](https://www.optionseducation.org/getmedia/9c73e607-a85e-4279-887a-574d0308d593/Short-Condor-PnL.png?width=260&height=260 "Short Condor P&L chart; Short 55 put & 65 call (green dots), Long 50 put & 70 call (red dots); Max loss between 55-65, Max profit below 50 or above 70")

Net Position (at expiration)

### Example

*   Long 1 XYZ 70 call
*   Short 1 XYZ 65 call
*   Short 1 XYZ 55 put
*   Long 1 XYZ 50 put

**MAXIMUM GAIN**

*   Net premium received

**MAXIMUM LOSS**

*   (High call strike - low call strike) OR (High put strike- low put strike) - net premium received

### Motivation

The investor hopes the underlying stock will stay within a certain range by expiration.

### Variations

This strategy is a variation of the [short iron butterfly](https://www.optionseducation.org/strategies/all-strategies/short-iron-butterfly). Instead of a body and two wings, the body has been split into two different strikes so that there are two shoulders in the middle and two wingtips outside the shoulders.

### Max Loss

The maximum loss would occur should the underlying stock be above the upper call strike or below the lower put strike at expiration. In that case either both calls or both puts would be in-the-money. The loss would be the difference between either the call strikes or the put strikes (whichever are in-the-money), less the premium received for initiating the position.

### Max Gain

The maximum gain would occur should the underlying stock be between the lower call strike and upper put strike at expiration. In that case all the options would expire worthless, and the premium received to initiate the position could be pocketed.

### Profit/Loss

The potential profit and loss are both very limited. In essence, a condor at expiration has a minimum value of zero and a maximum value equal to the span of either wing. An investor who sells a condor receives a premium somewhere between the minimum and maximum value, and profits if the condor's value moves toward the minimum as expiration approaches.

### Breakeven

This strategy breaks even if at expiration the underlying stock is either above the lower call strike or below the upper put strike by the amount of the premium received to initiate the position.

Upside breakeven = lower call strike + premiums received

Downside breakeven = upper put strike - premiums received

### Volatility

An increase in implied volatility, all other things equal, would have a negative impact on this strategy.

### Time Decay

The passage of time, all other things equal, will have a positive effect on this strategy.

### Assignment Risk

The short options that form the shoulders of the condor's wings are subject to exercise at any time, while the investor decides if and when to exercise the wingtips. If an early exercise occurs at either shoulder, the investor can choose whether to close out the resulting position in the market or to exercise the appropriate wingtip.

It is possible, however, that the underlying stock will be outside the wingtips and the investor will want to exercise one of their shoulders, thereby locking in the maximum loss. In addition, the other half of the position would remain, with the potential to go against the investor and create still further losses. Exercising an option to close out a position resulting from assignment on a short option will require borrowing or financing stock for one business day.

And be aware, a situation where a stock is involved in a restructuring or capitalization event, such as a merger, takeover, spin-off or special dividend, could completely upset typical expectations regarding early exercise of options on the stock.

### Expiration Risk

If at expiration the stock is trading near either shoulder the investor would face uncertainty as to whether or not they would be assigned. Should the exercise activity be other than expected, the investor could be unexpectedly long or short the stock on the Monday following expiration and hence subject to an adverse move over the weekend.

### Comments

N/A

### Related Position

Comparable Position: N/A

Opposite Position: [Long Condor](https://www.optionseducation.org/strategies/all-strategies/long-iron-condor)