"""从链快照派生波动率视图（v1 规则，无 LLM）。

按顺序判，先命中先返回：
1. 财报等催化剂在 10 个自然日内 -> rising；
2. 近月 ATM IV > 远月 ATM IV * 1.10（事件定价倒挂） -> rising；
   近月 ATM IV < 远月 ATM IV * 0.90 -> falling；
3. 前两条判不出方向时，才看 IV/HV 基准：IV/HV >= 1.15 -> rising，<= 1/1.15 -> falling；
4. 其余 -> neutral；链和基准都判不出 -> unknown。
"""

from __future__ import annotations

from datetime import date

from ..schema import ChainSnapshot, EnsembleSignal, VolatilityView

IV_HV_RISING_RATIO = 1.15


def derive_volatility_view(
    signal: EnsembleSignal,
    chain: ChainSnapshot | None,
    *,
    event_window_days: int = 10,
    today: date | None = None,
    vol_basis=None,
    iv_hv_rising_ratio: float = IV_HV_RISING_RATIO,
) -> VolatilityView:
    today = today or date.today()

    for c in signal.catalysts:
        if c.type == "dividend":
            # 除息不是波动率事件，由 risk 的 ex_div_blackout_days 单独管。
            continue
        if c.expected_date and 0 <= (c.expected_date - today).days <= event_window_days:
            return "rising"

    term = _term_structure(chain)
    if term in ("rising", "falling"):
        return term
    basis = _ratio_view(vol_basis, iv_hv_rising_ratio)
    if basis:
        return basis
    return "neutral" if term == "neutral" else "unknown"


def _term_structure(chain: ChainSnapshot | None) -> str | None:
    """近远月 ATM IV 比价。链不足时返回 None（判不出，不是中性）。"""
    if chain is None or chain.spot is None:
        return None
    expiries = chain.expiries()
    if len(expiries) < 2:
        return None
    front = chain.atm_iv(expiries[0])
    back = chain.atm_iv(expiries[-1])
    if not front or not back:
        return None
    if front > back * 1.10:
        return "rising"
    if front < back * 0.90:
        return "falling"
    return "neutral"


def _ratio_view(vol_basis, threshold: float) -> str | None:
    """IV/HV 基准。缺基准时返回 None，不猜。"""
    ratio = getattr(vol_basis, "ratio", None)
    if ratio is None or threshold <= 0:
        return None
    if ratio >= threshold:
        return "rising"
    if ratio <= 1.0 / threshold:
        return "falling"
    return None
