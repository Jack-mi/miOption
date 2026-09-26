"""引擎报告与标的快照的缺数判定。确定性规则，不让 LLM 填空。"""

from __future__ import annotations

from ..schema.underlying import UnderlyingSnapshot
from .base import RawBundle

# 整词命中，或同一段里同时出现「缺失」和行情/日线。
_EXPLICIT = (
    "NoMarketDataError",
    "数据缺失",
    "行情缺失",
    "日线缺失",
    "缺少行情",
    "缺少日线",
    "无行情数据",
)


def report_data_gaps(text: str) -> list[str]:
    hits = [m for m in _EXPLICIT if m in text]
    if not hits and "缺失" in text and ("行情" in text or "日线" in text):
        hits = ["行情或日线缺失"]
    if not hits:
        return []
    return [f"报告标明关键数据缺失: {', '.join(hits)}"]


def apply_data_gate(
    bundle: RawBundle,
    text: str,
    snapshot: UnderlyingSnapshot | None,
) -> RawBundle:
    """富途缺报价或日线才整票弃权。引擎自报缺数时保留方向，标为 opinion。"""
    report_gaps = report_data_gaps(text)
    snap_gaps = [] if snapshot is None else snapshot.critical_gaps()
    if snap_gaps or (snapshot is None and report_gaps):
        gaps = list(report_gaps)
        for gap in snap_gaps:
            if gap not in gaps:
                gaps.append(gap)
        bundle.data_gaps = gaps
        bundle.data_status = "insufficient_data"
        return bundle
    if report_gaps:
        bundle.data_gaps = report_gaps
        bundle.data_status = "opinion"
        return bundle
    bundle.data_gaps = []
    bundle.data_status = "actionable"
    return bundle
