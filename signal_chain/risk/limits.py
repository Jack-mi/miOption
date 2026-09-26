"""确定性风控闸 —— 借 aihf risk/limits 哲学：LLM 的影响力止于信号，此后全是算术。

一票否决项（方案 v5）：
- conflicted 信号；
- 财报窗口（earnings_blackout_days）内的 short-vol 结构；volatility_view=rising 时 short-vol；
- 单腿流动性不达标：OI < min_open_interest 或 spread_pct > max_spread_pct；
- 单标的新结构最大亏损 > max_position_risk_pct * 账户权益（美股为总资产折美元；读取失败时跳过并告警）。
"""

from __future__ import annotations

from datetime import date

from ..schema import (
    ChainSnapshot,
    EnsembleSignal,
    RiskDecision,
    StrategyProposal,
)


def _find_row(chain: ChainSnapshot, code: str):
    for r in chain.rows:
        if r.code == code:
            return r
    return None


def check_signal(signal: EnsembleSignal) -> RiskDecision:
    """信号级门禁：conflicted 直接否。"""
    vetoes: list[str] = []
    if signal.agreement == "insufficient_data":
        detail = signal.quality_notes or "缺关键报价或日线"
        vetoes.append(f"数据不足（insufficient_data）：{detail}")
    if signal.agreement == "conflicted":
        vetoes.append("信号分歧（conflicted）：双引擎方向异号，默认不行动")
    return RiskDecision(approved=not vetoes, vetoes=vetoes)


def check_proposal(
    proposal: StrategyProposal,
    signal: EnsembleSignal,
    chain: ChainSnapshot,
    *,
    earnings_blackout_days: int = 10,
    min_open_interest: int = 100,
    max_spread_pct: float = 0.10,
    account_equity: float | None = None,
    equity_currency: str | None = None,
    equity_note: str | None = None,
    max_position_risk_pct: float = 0.05,
    today: date | None = None,
) -> RiskDecision:
    """结构级门禁：对每条腿做流动性校验，对整体做 short-vol 与敞口校验。"""
    today = today or date.today()
    vetoes: list[str] = []
    warnings: list[str] = []

    if proposal.is_short_vol:
        for c in signal.catalysts:
            if c.type == "earnings" and c.expected_date:
                gap = (c.expected_date - today).days
                if 0 <= gap <= earnings_blackout_days:
                    vetoes.append(
                        f"财报窗口内禁止 short-vol：{c.expected_date} 财报（{gap} 天后），结构 {proposal.name}"
                    )
        if signal.volatility_view == "rising":
            vetoes.append(f"volatility_view=rising 时禁止 short-vol 结构：{proposal.name}")

    for leg in proposal.legs:
        row = _find_row(chain, leg.code)
        if row is None:
            vetoes.append(f"腿 {leg.code} 不在链快照中，无法校验流动性")
            continue
        if row.open_interest is not None and row.open_interest < min_open_interest:
            vetoes.append(f"腿 {leg.code} OI={row.open_interest} < {min_open_interest}")
        if row.bid is not None and row.bid <= 0:
            vetoes.append(f"腿 {leg.code} 无买盘报价（bid=0），不可交易")
        sp = row.spread_pct
        if sp is not None and sp > max_spread_pct:
            vetoes.append(f"腿 {leg.code} 买卖价差 {sp:.1%} > {max_spread_pct:.0%}")
        if row.open_interest is None and row.spread_pct is None:
            warnings.append(f"腿 {leg.code} 缺少 OI/报价数据，流动性未校验")

    if account_equity is None:
        warnings.append("Futu 账户权益读取失败，跳过敞口上限检查")
    elif proposal.max_loss is not None and proposal.max_loss > max_position_risk_pct * account_equity:
        currency = equity_currency or "账户币种"
        note = f"（{equity_note}）" if equity_note else ""
        vetoes.append(
            f"最大亏损 {proposal.max_loss:.0f} {currency} 超过单标的上限 "
            f"{max_position_risk_pct:.0%} x {account_equity:.0f} {currency}{note}"
        )

    return RiskDecision(approved=not vetoes, vetoes=vetoes, warnings=warnings)
