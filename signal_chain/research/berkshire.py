"""ai-berkshire 只提供基本面交叉验证和财报日。不跑投研团队，不猜缺失日期。

financial-data 规定两源误差超过 1% 要标出。数字对账调用
`ai-berkshire/tools/financial_rigor.py` 的 cross_validate。没有两份独立数值时，
基本面保持 unsupported。earnings-review 没有可调用的披露日接口，调用方给出
日期和出处才写入快照，否则保持空。
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
from datetime import date, datetime

from ..config import REPO_ROOT
from ..schema import Catalyst
from ..schema.underlying import FieldMeta, UnderlyingSnapshot

BERKSHIRE_ROOT = REPO_ROOT.parent / "ai-berkshire"
_TOLERANCE_PCT = 1.0


def _cross_validate(field: str, values: dict[str, float]):
    path = BERKSHIRE_ROOT / "tools" / "financial_rigor.py"
    spec = importlib.util.spec_from_file_location("financial_rigor", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"找不到 financial_rigor: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with contextlib.redirect_stdout(io.StringIO()):
        return mod.cross_validate(field, values, tolerance_pct=_TOLERANCE_PCT)


def attach_fundamentals(
    snapshot: UnderlyingSnapshot,
    *,
    metric: str,
    period: str,
    values: dict[str, float],
    as_of: date,
    fetched_at: datetime,
) -> UnderlyingSnapshot:
    """两源以上且偏差 ≤1% 才标 available。不把共识数值写进快照。"""
    if len(values) < 2:
        meta = FieldMeta(
            status="missing",
            source="financial-data",
            as_of=as_of,
            fetched_at=fetched_at,
            period=period,
            error=f"{metric} 缺少第二个独立来源",
        )
        return snapshot.model_copy(update={"fundamentals": meta})
    result = _cross_validate(metric, values)
    sources = ",".join(values)
    if not result["all_consistent"]:
        meta = FieldMeta(
            status="missing",
            source=sources,
            as_of=as_of,
            fetched_at=fetched_at,
            period=period,
            error=f"{metric} 两源偏差超过 {_TOLERANCE_PCT:.0f}%",
        )
        return snapshot.model_copy(update={"fundamentals": meta})
    meta = FieldMeta(
        status="available",
        source=sources,
        as_of=as_of,
        fetched_at=fetched_at,
        period=period,
        error=None,
    )
    return snapshot.model_copy(update={"fundamentals": meta})


def note_earnings(
    snapshot: UnderlyingSnapshot,
    expected: date | None,
    *,
    source: str | None,
) -> UnderlyingSnapshot:
    """没有披露日就不写。source 必须是公告或交易所出处，不是模型推断。"""
    if expected is None:
        return snapshot
    if not source:
        raise ValueError("财报日缺少出处")
    return snapshot.model_copy(update={
        "earnings_date": expected,
        "earnings_source": source,
    })


def earnings_catalyst(snapshot: UnderlyingSnapshot) -> Catalyst | None:
    if snapshot.earnings_date is None:
        return None
    return Catalyst(
        type="earnings",
        expected_date=snapshot.earnings_date,
        description=snapshot.earnings_source or "",
    )
