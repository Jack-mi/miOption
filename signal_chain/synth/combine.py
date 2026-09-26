"""Ensemble 合成规则 —— 纯确定性代码，无 LLM。

规则（方案 v5 锁定）：
- 时间对齐：两信号 as_of 相差 > max_asof_gap_days 时，旧者 degraded 仅作参考；
- 富途缺报价/日线（data_status=insufficient_data）才弃权，不进入投票；
- opinion 是引擎自身没行情但仍保留的观点，与 actionable 一样投票；
- 全部弃权 -> insufficient_data，方向中性，不拿缺数票凑合成；
- 同向且档位差 <=1 -> aligned，conviction = 均值 * aligned_boost（封顶 ±1）；
- 一方向 + 一中性 -> partial，conviction = 简单平均；
- 方向异号 -> conflicted，conviction 取平均，下游默认不行动；
- 单源 -> single_source，conviction * single_source_discount。
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


_OPINION_NOTE = "自身未取到行情，观点保留，价格以富途快照为准"
_FUTU_ONLY_NOTE = "价格证据只有富途，不是双源行情互证"


def _quality_note(voting: list[EngineSignal], abstain: str | None) -> str | None:
    parts: list[str] = []
    if any(s.data_status == "opinion" for s in voting):
        parts.append(_OPINION_NOTE)
    if voting and all(s.data_status == "opinion" for s in voting):
        parts.append(_FUTU_ONLY_NOTE)
    if abstain:
        parts.append(abstain)
    return " | ".join(parts) or None


def _abstain_note(signals: list[EngineSignal]) -> str | None:
    parts = []
    for s in signals:
        if s.data_status != "insufficient_data":
            continue
        gaps = "；".join(s.data_gaps) if s.data_gaps else "缺关键报价或日线"
        parts.append(f"{s.engine}: {gaps}")
    if not parts:
        return None
    return "弃权 " + " | ".join(parts)


def combine(
    signals: list[EngineSignal],
    *,
    as_of: date,
    aligned_boost: float = 1.2,
    single_source_discount: float = 0.7,
    max_asof_gap_days: int = 1,
) -> EnsembleSignal:
    """把全部可投票的 EngineSignal 合成。notes/dissent 由 Claude Agent SDK 后补。"""
    if not signals:
        raise ValueError("combine() 需要至少一条信号")

    signals = align_asof(signals, max_asof_gap_days)
    voting = [s for s in signals if s.data_status != "insufficient_data" and not s.degraded]
    if not voting:
        # 缺数票不能回退成有效票。仅 as-of / 抽取降级、数据仍可行动的，沿用原降级回退。
        voting = [s for s in signals if s.data_status != "insufficient_data"]
    note = _quality_note(voting, _abstain_note(signals))
    if not voting:
        return EnsembleSignal(
            ticker=signals[0].ticker,
            market=signals[0].market,
            as_of=as_of,
            components=signals,
            agreement="insufficient_data",
            direction=Direction.NEUTRAL,
            conviction=0.0,
            quality_notes=note or "无可信报价或日线，信号弃权",
        )

    first = voting[0]
    if len(voting) == 1:
        conviction = round(first.conviction * single_source_discount, 4)
        agreement: Agreement = "single_source"
    else:
        signs = [_SIGN[s.direction] for s in voting]
        avg = sum(s.conviction for s in voting) / len(voting)
        tiers = [_TIER[s.direction] for s in voting]
        if any(s > 0 for s in signs) and any(s < 0 for s in signs):
            agreement = "conflicted"
            conviction = avg
        elif any(s == 0 for s in signs) and any(s != 0 for s in signs):
            agreement = "partial"
            conviction = avg
        elif max(tiers) - min(tiers) <= 1:
            agreement = "aligned"
            conviction = max(-1.0, min(1.0, avg * aligned_boost))
        else:
            agreement = "partial"
            conviction = avg
        conviction = round(conviction, 4)

    vol_views = {s.volatility_view for s in voting}
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
        catalysts=_merge_catalysts(voting),
        quality_notes=note,
    )
