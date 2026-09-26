"""固定投研工作流。四个角色只读本轮切片。缺字段的包由代码写成缺失。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from ..decision.ratings import RATING_MAP as _RATING_MAP
from ..data.models import MarketData

VERSION = "1"
_MAX_PACKETS = 4
_MAX_MODEL_CALLS = 3

_GAP_TEXT = {
    "business": "商业模式：缺失，没有对应字段。",
    "competition": "竞争：缺失，没有对应字段。",
    "risk": "风险：缺失，没有对应字段。",
}
ROLE_GAPS = ["商业模式缺失", "竞争缺失", "风险缺失"]

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_TOC_HEADING = re.compile(r"\d{1,3}\s+[A-Z]")
_MEMO_CLIP = 180


def looks_like_toc(text: str) -> bool:
    """代理声明目录是连续的页码加标题，不是风险正文。"""
    return len(_TOC_HEADING.findall(text)) >= 4


def clip_memo(text: str, limit: int = _MEMO_CLIP) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


class FinanceDraft(BaseModel):
    rating: str
    claims: list[str] = []


class VerifyDraft(BaseModel):
    accepted: list[str] = []


class IntegrateDraft(BaseModel):
    rating: str
    analysis: str = ""


_FINANCE_SCHEMA = {
    "type": "object",
    "properties": {
        "rating": {"type": "string", "enum": ["buy", "overweight", "hold", "underweight", "sell"]},
        "claims": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["rating", "claims"],
    "additionalProperties": False,
}
_VERIFY_SCHEMA = {
    "type": "object",
    "properties": {"accepted": {"type": "array", "items": {"type": "string"}}},
    "required": ["accepted"],
    "additionalProperties": False,
}
_INTEGRATE_SCHEMA = {
    "type": "object",
    "properties": {
        "rating": {"type": "string", "enum": ["buy", "overweight", "hold", "underweight", "sell"]},
        "analysis": {"type": "string"},
    },
    "required": ["rating", "analysis"],
    "additionalProperties": False,
}


@dataclass
class Packet:
    id: str
    status: str
    text: str
    model_call: bool = False


@dataclass
class WorkflowRun:
    version: str
    model: str | None
    ticker: str
    as_of: str
    packets: list[Packet] = field(default_factory=list)
    accepted_claims: list[str] = field(default_factory=list)
    rejected_claims: list[str] = field(default_factory=list)
    rating: str | None = None
    abstain_reason: str | None = None
    calls: list[dict] = field(default_factory=list)
    role_gaps: list[str] = field(default_factory=list)
    memo: str = ""

    @property
    def model_calls(self) -> int:
        return len(self.calls)


def finance_slice(market: MarketData) -> str:
    snap = market.snapshot
    lines = ["## 财务切片"]
    fund = snap.fundamentals
    if fund.status == "available":
        period = fund.period or "无期间"
        lines.append(f"- 财务: available，出处 {fund.source or '无出处'}，期间 {period}")
    else:
        lines.append(f"- 财务缺失: {fund.error or fund.status}")
    for ratio in market.ratios:
        lines.append(f"- {ratio.metric}: {ratio.value}，出处 {ratio.source}，期间 {ratio.period}")
    if market.facts:
        for fact in market.facts:
            lines.append(
                f"- 单源 {fact.metric}: {fact.value}，出处 {fact.source}，期间 {fact.period}"
            )
    else:
        lines.append("- 单源营收缺失")
    if snap.earnings_date is not None:
        lines.append(f"- 财报日: {snap.earnings_date.isoformat()}，出处 {snap.earnings_source}")
    else:
        lines.append("- 财报日缺失")
    return "\n".join(lines)


def gap_memo() -> str:
    return " ".join(_GAP_TEXT[key] for key in ("business", "competition", "risk"))


def role_packets(market: MarketData) -> list[Packet]:
    by = {item.section: item for item in market.excerpts}
    business = by.get("business")
    risk_bits = []
    for key in ("risk_factors", "governance"):
        item = by.get(key)
        if item is None:
            continue
        if key == "governance" and looks_like_toc(item.text):
            continue
        risk_bits.append(item.text)
    competition = by.get("competition")
    packets = [
        Packet("business", "excerpt", f"商业模式：{business.text}") if business
        else Packet("business", "gap", _GAP_TEXT["business"]),
        Packet("competition", "excerpt", f"竞争：{competition.text}") if competition
        else Packet("competition", "gap", _GAP_TEXT["competition"]),
        Packet("risk", "excerpt", "风险：" + " ".join(risk_bits)) if risk_bits
        else Packet("risk", "gap", _GAP_TEXT["risk"]),
    ]
    return packets


def role_memo(market: MarketData) -> str:
    return " ".join(clip_memo(packet.text) for packet in role_packets(market))


def role_gap_labels(market: MarketData) -> list[str]:
    labels = {"business": "商业模式缺失", "competition": "竞争缺失", "risk": "风险缺失"}
    return [labels[packet.id] for packet in role_packets(market) if packet.status == "gap"]


def _numbers(text: str) -> set[str]:
    return set(_NUMBER.findall(text))


def claims_in_slice(claims: list[str], slice_text: str) -> tuple[list[str], list[str]]:
    allowed = _numbers(slice_text)
    kept: list[str] = []
    dropped: list[str] = []
    for claim in claims:
        nums = _numbers(claim)
        if nums and not nums <= allowed:
            dropped.append(claim)
        else:
            kept.append(claim)
    return kept, dropped


def _call_meta(agent: str, meta) -> dict:
    if meta is None:
        return {"agent": agent, "thread_id": None, "usage": None}
    usage = getattr(meta, "usage", None)
    return {
        "agent": agent,
        "thread_id": getattr(meta, "thread_id", None),
        "usage": usage,
    }


def _finish(run: WorkflowRun, finance: Packet, market: MarketData) -> WorkflowRun:
    roles = role_packets(market)
    run.role_gaps = role_gap_labels(market)
    run.packets = [*roles, finance]
    if len(run.packets) > _MAX_PACKETS:
        raise RuntimeError("角色包超过预算")
    if run.model_calls > _MAX_MODEL_CALLS:
        raise RuntimeError("模型调用超过预算")
    body = role_memo(market)
    if run.accepted_claims:
        body = f"{body} 财务：{' '.join(run.accepted_claims)}"
    if run.abstain_reason:
        body = f"{body} {run.abstain_reason}"
    run.memo = body
    return run


async def run_workflow(
    market: MarketData,
    runner,
    model: str | None,
    *,
    trace_dir: Path | None = None,
) -> WorkflowRun:
    snap = market.snapshot
    run = WorkflowRun(
        version=VERSION,
        model=model,
        ticker=snap.ticker,
        as_of=snap.as_of.isoformat(),
    )
    if snap.fundamentals.status != "available":
        finished = _finish(run, Packet("finance", "abstain", "财务未标可用，价值信号弃权"), market)
        finished.abstain_reason = "财务未标可用，价值信号弃权"
        finished.memo = f"{role_memo(market)} {finished.abstain_reason}"
        _write_trace(finished, trace_dir)
        return finished
    if runner is None or not model:
        finished = _finish(run, Packet("finance", "abstain", "未调用模型，价值信号弃权"), market)
        finished.abstain_reason = "未调用模型，价值信号弃权"
        finished.memo = f"{role_memo(market)} {finished.abstain_reason}"
        _write_trace(finished, trace_dir)
        return finished

    slice_text = finance_slice(market)
    try:
        draft, meta = await runner.run_json(
            "finance", model,
            "你只根据财务切片写主张。不要用价格或资金流。"
            "rating 只能是 buy、overweight、hold、underweight、sell。"
            "claims 每条是一句财务事实，数字必须来自切片。\n\n"
            f"{slice_text}",
            FinanceDraft,
            output_schema=_FINANCE_SCHEMA,
        )
    except Exception as exc:
        run.abstain_reason = f"财务工人失败: {str(exc)[:160]}"
        finished = _finish(run, Packet("finance", "abstain", run.abstain_reason, True), market)
        _write_trace(finished, trace_dir)
        return finished
    run.calls.append(_call_meta("finance", meta))

    worker_claims = [c.strip() for c in draft.claims if c and c.strip()]
    if not worker_claims:
        run.abstain_reason = "财务没有可核验的主张"
        finished = _finish(run, Packet("finance", "abstain", run.abstain_reason, True), market)
        _write_trace(finished, trace_dir)
        return finished

    listed = "\n".join(f"- {c}" for c in worker_claims)
    try:
        checked, meta = await runner.run_json(
            "verify", model,
            "你只核验下列主张是否被财务切片支持。不要新增主张，不要改写缺失。"
            "accepted 里只保留切片能对上的原句。\n\n"
            f"主张:\n{listed}\n\n{slice_text}",
            VerifyDraft,
            output_schema=_VERIFY_SCHEMA,
        )
    except Exception as exc:
        run.abstain_reason = f"财务核验失败: {str(exc)[:160]}"
        run.rejected_claims = list(worker_claims)
        finished = _finish(run, Packet("finance", "abstain", run.abstain_reason, True), market)
        _write_trace(finished, trace_dir)
        return finished
    run.calls.append(_call_meta("verify", meta))

    proposed = [c for c in checked.accepted if c in worker_claims]
    kept, dropped_numbers = claims_in_slice(proposed, slice_text)
    rejected = [c for c in worker_claims if c not in kept]
    run.accepted_claims = kept
    run.rejected_claims = rejected
    if dropped_numbers and not kept:
        run.abstain_reason = "财务主张未通过核验"
        finished = _finish(run, Packet("finance", "rejected", run.abstain_reason, True), market)
        _write_trace(finished, trace_dir)
        return finished
    if not kept:
        run.abstain_reason = "财务主张未通过核验"
        finished = _finish(run, Packet("finance", "rejected", run.abstain_reason, True), market)
        _write_trace(finished, trace_dir)
        return finished

    memo_so_far = f"{role_memo(market)} 财务：{' '.join(kept)}"
    try:
        integrated, meta = await runner.run_json(
            "integrate", model,
            "你只根据下面已经核验的财务段和三份缺失说明给出评级。"
            "不能把缺失写成事实，也不能改用价格或资金流。"
            "rating 只能是 buy、overweight、hold、underweight、sell。\n\n"
            f"{memo_so_far}",
            IntegrateDraft,
            output_schema=_INTEGRATE_SCHEMA,
        )
    except Exception as exc:
        run.abstain_reason = f"价值信号汇总失败: {str(exc)[:160]}"
        finished = _finish(run, Packet("finance", "verified", memo_so_far, True), market)
        _write_trace(finished, trace_dir)
        return finished
    run.calls.append(_call_meta("integrate", meta))
    mapped = _RATING_MAP.get(str(integrated.rating).strip().lower())
    if mapped is None:
        run.abstain_reason = f"价值信号评级无法识别: {integrated.rating}"
        finished = _finish(run, Packet("finance", "verified", memo_so_far, True), market)
        _write_trace(finished, trace_dir)
        return finished
    run.rating = str(integrated.rating).strip().lower()
    analysis = integrated.analysis.strip()
    if analysis and _numbers(analysis) <= _numbers(memo_so_far):
        memo_so_far = f"{memo_so_far} {analysis}"
    run.memo = memo_so_far
    run.role_gaps = role_gap_labels(market)
    run.packets = [
        *role_packets(market),
        Packet("finance", "verified", " ".join(kept), True),
    ]
    if run.model_calls > _MAX_MODEL_CALLS:
        raise RuntimeError("模型调用超过预算")
    _write_trace(run, trace_dir)
    return run


def _write_trace(run: WorkflowRun, trace_dir: Path | None) -> None:
    if trace_dir is None:
        return
    trace_dir.mkdir(parents=True, exist_ok=True)
    path = trace_dir / f"{run.as_of}_{run.ticker.replace('.', '-')}.jsonl"
    row = {
        "version": run.version,
        "model": run.model,
        "ticker": run.ticker,
        "as_of": run.as_of,
        "packets": [{"id": p.id, "status": p.status, "text": p.text} for p in run.packets],
        "accepted_claims": run.accepted_claims,
        "rejected_claims": run.rejected_claims,
        "rating": run.rating,
        "abstain_reason": run.abstain_reason,
        "calls": run.calls,
    }
    path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
