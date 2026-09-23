"""从链快照派生波动率视图（v1 规则，无 LLM）。

- 财报等催化剂在 10 个自然日内 -> rising；
- 近月 ATM IV > 远月 ATM IV * 1.10（事件定价倒挂） -> rising；
- 近月 ATM IV < 远月 ATM IV * 0.90 -> falling；
- 其余 -> neutral；数据不足 -> unknown。
"""

from __future__ import annotations

from datetime import date

from ..schema import ChainSnapshot, EnsembleSignal, VolatilityView


def derive_volatility_view(
    signal: EnsembleSignal,
    chain: ChainSnapshot | None,
    *,
    event_window_days: int = 10,
    today: date | None = None,
) -> VolatilityView:
    today = today or date.today()

    for c in signal.catalysts:
        if c.expected_date and 0 <= (c.expected_date - today).days <= event_window_days:
            return "rising"

    if chain is None or chain.spot is None:
        return "unknown"
    expiries = chain.expiries()
    if len(expiries) < 2:
        return "unknown"
    front = chain.atm_iv(expiries[0])
    back = chain.atm_iv(expiries[-1])
    if not front or not back:
        return "unknown"
    if front > back * 1.10:
        return "rising"
    if front < back * 0.90:
        return "falling"
    return "neutral"
