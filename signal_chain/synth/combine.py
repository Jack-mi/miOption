"""Ensemble 合成规则 —— 纯确定性代码，无 LLM。

规则（方案 v5 锁定）：
- 时间对齐：两信号 as_of 相差 > max_asof_gap_days 时，旧者 degraded 仅作参考；
- 同向且档位差 <=1 -> aligned，conviction = 均值 * aligned_boost（封顶 ±1）；
- 一方向 + 一中性 -> partial，conviction = 简单平均；
- 方向异号 -> conflicted，conviction 取平均，下游默认不行动；
- 单源 -> single_source，conviction * single_source_discount，degraded=True。
"""

from __future__ import annotations

from datetime import date

from ..schema import (
    Agreement,
    Catalyst,
    Direction,
    EngineSignal,
    EnsembleSignal,
)

_SIGN = {
    Direction.STRONG_BUY: 1,
    Direction.BUY: 1,
    Direction.NEUTRAL: 0,
    Direction.SELL: -1,
    Direction.STRONG_SELL: -1,
}

_TIER = {
    Direction.STRONG_BUY: 2,
    Direction.BUY: 1,
    Direction.NEUTRAL: 0,
    Direction.SELL: -1,
    Direction.STRONG_SELL: -2,
}


def direction_from_conviction(v: float) -> Direction:
    if v >= 0.6:
        return Direction.STRONG_BUY
    if v >= 0.2:
        return Direction.BUY
    if v > -0.2:
        return Direction.NEUTRAL
    if v > -0.6:
        return Direction.SELL
    return Direction.STRONG_SELL


def _merge_catalysts(signals: list[EngineSignal]) -> list[Catalyst]:
    seen: set[tuple[str, str | None]] = set()
    out: list[Catalyst] = []
    for s in signals:
        for c in s.catalysts:
            key = (c.type, c.expected_date.isoformat() if c.expected_date else None)
            if key not in seen:
                seen.add(key)
                out.append(c)
    return out


def align_asof(signals: list[EngineSignal], max_gap_days: int) -> list[EngineSignal]:
    """as_of 相差过大的旧信号降级（保留但 degraded），以最新者为准。"""
    if len(signals) < 2:
        return signals
    newest = max(s.as_of for s in signals)
    out = []
    for s in signals:
        if (newest - s.as_of).days > max_gap_days:
            note = (s.quality_notes or "") + " | as_of 错位降级"
            s = s.model_copy(update={"degraded": True, "quality_notes": note})
        out.append(s)
    return out


def combine(
    signals: list[EngineSignal],
    *,
    as_of: date,
    aligned_boost: float = 1.2,
    single_source_discount: float = 0.7,
    max_asof_gap_days: int = 1,
) -> EnsembleSignal:
    """把 1~2 条 EngineSignal 合成 EnsembleSignal（notes/dissent 由 Codex 后补）。"""
    if not signals:
        raise ValueError("combine() 需要至少一条信号")

    signals = align_asof(signals, max_asof_gap_days)
    active = [s for s in signals if not s.degraded] or signals

    first = active[0]
    if len(active) == 1:
        conviction = round(first.conviction * single_source_discount, 4)
        agreement: Agreement = "single_source"
    else:
        a, b = active[0], active[1]
        sa, sb = _SIGN[a.direction], _SIGN[b.direction]
        avg = (a.conviction + b.conviction) / 2
        if sa != 0 and sa == sb and abs(_TIER[a.direction] - _TIER[b.direction]) <= 1:
            agreement = "aligned"
            conviction = max(-1.0, min(1.0, avg * aligned_boost))
        elif sa == 0 or sb == 0:
            agreement = "partial"
            conviction = avg
        else:
            agreement = "conflicted"
            conviction = avg
        conviction = round(conviction, 4)

    vol_views = {s.volatility_view for s in active}
    if "rising" in vol_views:
        vol = "rising"
    elif vol_views == {"neutral"}:
        vol = "neutral"
    elif "falling" in vol_views and "rising" not in vol_views:
        vol = "falling"
    else:
        vol = "unknown"

    return EnsembleSignal(
        ticker=first.ticker,
        market=first.market,
        as_of=as_of,
        components=signals,
        agreement=agreement,
        direction=direction_from_conviction(conviction),
        conviction=conviction,
        volatility_view=vol,  # type: ignore[arg-type]
        catalysts=_merge_catalysts(active),
    )
