# Short Iron Butterfly

This strategy profits if the underlying stock is inside the wings of the iron butterfly at expiration.

### Description

A short iron butterfly consists of being long a call at an upper strike, short a call and short a put at a middle strike, and long a put at a lower strike. The upper and lower strikes (wings) must both be equidistant from the middle strike (body), and all the options must be the same expiration. An alternative way to think about this strategy is a [short straddle](https://www.optionseducation.org/strategies/all-strategies/short-straddle) surrounded by a [long strangle](https://www.optionseducation.org/strategies/all-strategies/long-straddle).  It could also be considered as a [bear call spread](https://www.optionseducation.org/strategies/all-strategies/bear-call-spread-credit-call-spread) and a [bull put spread](https://www.optionseducation.org/strategies/all-strategies/bull-put-spread-credit-put-spread).

### Outlook

The investor is looking for the underlying stock to trade in a narrow range during the life of the options.

### Summary

This strategy works better if the underlying stock is inside the wings of the iron butterfly at expiration.

![Short Iron Butterfly P&L chart; Max profit at 60 (green dot); Max loss at 55 and 65 (red dots)](https://www.optionseducation.org/getmedia/f5179fa6-3a4c-4b1a-bac9-545d8ee8c594/Short-Iron-Butterfly-PnL.png?width=260&height=260 "Short Iron Butterfly P&L chart; Max profit at 60 (green dot); Max loss at 55 and 65 (red dots)")

Net Position (at expiration)

### Example

*   Long 1 XYZ 65 call
*   Short 1 XYZ 60 call
*   Short 1 XYZ 60 put
*   Long 1 XYZ 55 put

**MAXIMUM GAIN**

*   Net premium received

**MAXIMUM LOSS**

*   High strike - middle strike - net premium received

### Motivation

Earn income by predicting a period of neutral movement in the underlying.

### Variations

While this strategy has a similar risk/reward profile to the long butterflies (both call and put), the short iron butterfly differs in that a positive cash flow occurs up front, and any negative cash flow is uncertain and would occur somewhere in the future.

### Max Loss

The maximum loss would occur should the underlying stock be outside the wings at expiration. In that case either both calls or both puts would be in-the-money.  The loss would be the difference between the body and either wing, less the premium received for initiating the position.

### Max Gain

The maximum gain would occur should the underlying stock be at the body of the butterfly at expiration. In that case all the options would expire worthless, and the premium received to initiate the position could be pocketed.

### Profit/Loss

The potential profit and loss are both very limited. In essence, an iron butterfly at expiration has a minimum value of zero and a maximum value equal to the distance between either wing and the body. An investor who sells an iron butterfly receives a premium somewhere between the minimum and maximum value, and generally profits if the butterfly's value moves toward the minimum as expiration approaches.

### Breakeven

The strategy breaks even if at expiration the underlying stock is either above or below the body of the butterfly by the amount of premium received to initiate the position.

### Volatility

An increase in implied volatility, all other things equal, would have a negative impact on this strategy.

### Time Decay

The passage of time, all other things equal, will have a positive effect on this strategy.

### Assignment Risk

The short options that form the body of the butterfly are subject to exercise at any time, while the investor decides if and when to exercise the wings. If an early exercise occurs at the body, the investor can choose whether to close out the resulting position in the market or to exercise one of their options (put or call, whichever is appropriate).

It is possible, however, that the underlying stock will be outside the wings and the investor may have to consider exercising one of their options, thereby locking in the maximum loss. In addition, the other half of the position will remain, with the potential to go against the investor and create still further losses. Exercising an option to close out a position resulting from assignment on a short option would require borrowing or financing stock for one business day.

And be aware, a situation where a stock is involved in a restructuring or capitalization event, such as a merger, takeover, spin-off or special dividend, could completely upset typical expectations regarding early exercise of options on the stock.

### Expiration Risk

This strategy has expiration risk. If at expiration the stock is trading near the body of the butterfly, the investor faces uncertainty as to whether or not they will be assigned. Should the exercise activity be other than expected, the investor could be unexpectedly long or short the stock on the Monday following expiration and hence subject to an adverse move over the weekend.

### Comments

N/A

### Related Position

Comparable Position: [Long Call Butterfly](https://www.optionseducation.org/strategies/all-strategies/long-call-butterfly)

Opposite Position: [Long Iron Butterfly](https://www.optionseducation.org/strategies/all-strategies/long-iron-butterfly)