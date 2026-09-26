"""三个信号只读 MarketData。研究信号和价值信号未调用模型就弃权。"""

from __future__ import annotations

from pydantic import BaseModel

from ..adapters.base import RawBundle
from ..adapters.quality import apply_data_gate
from .ratings import RATING_MAP as _RATING_MAP
from ..data.models import MarketData
from ..research.workflow import ROLE_GAPS, gap_memo, run_workflow
from ..schema import Direction, EngineSignal, make_signal_id
from .pack import render_pack

_SCHEMA = {
    "type": "object",
    "properties": {
        "rating": {"type": "string", "enum": ["buy", "overweight", "hold", "underweight", "sell"]},
        "analysis": {"type": "string"},
    },
    "required": ["rating", "analysis"],
    "additionalProperties": False,
}


class _Rating(BaseModel):
    rating: str
    analysis: str = ""


def _bundle(engine: str, market: MarketData, direction: Direction | None, conviction: float,
            text: str, faces: str, gaps: list[str]) -> RawBundle:
    snap = market.snapshot
    bundle = RawBundle(
        engine=engine,
        ticker=snap.ticker,
        market=snap.market,
        as_of=snap.as_of,
        report_ref=engine,
        direction=direction,
        conviction=conviction,
        data_sources=["market_data"],
        texts={"analysis": text, "faces": faces},
        data_gaps=list(gaps),
    )
    gated = apply_data_gate(bundle, "", snap)
    if gated.data_status == "actionable" and gaps:
        gated.data_gaps = list(gaps)
    return gated


def _abstain(engine: str, market: MarketData, reason: str, faces: str = "") -> RawBundle:
    bundle = _bundle(engine, market, None, 0.0, reason, faces, [reason])
    if bundle.data_status != "insufficient_data":
        bundle.data_status = "insufficient_data"
        bundle.data_gaps = [reason]
    elif reason not in bundle.data_gaps:
        bundle.data_gaps = [*bundle.data_gaps, reason]
    return bundle


def trend_signal(market: MarketData) -> RawBundle:
    snap = market.snapshot
    points: list[int] = []
    faces: list[str] = []
    gaps: list[str] = []
    last = snap.quote.last
    sma = snap.technical.indicators.get("sma_5")
    if snap.technical.meta.status == "available" and sma is not None and last is not None:
        if last > sma:
            points.append(1)
            faces.append("技术面：价格在 5 日均线之上")
        elif last < sma:
            points.append(-1)
            faces.append("技术面：价格在 5 日均线之下")
        else:
            faces.append("技术面：价格等于 5 日均线")
    else:
        gaps.append("技术面没有可计分的均线")
    net = market.flow_net
    if snap.capital_flow.status == "available" and net is not None:
        if net > 0:
            points.append(1)
            faces.append(f"资金面：净流入 {net}")
        elif net < 0:
            points.append(-1)
            faces.append(f"资金面：净流出 {net}")
        else:
            faces.append("资金面：净额为 0")
    else:
        gaps.append("资金面没有净额")
    side = []
    if snap.fundamentals.status == "available":
        side.append("旁证：财务可用")
    if market.news_text:
        side.append("旁证：有新闻标题")
    if not points:
        direction, conviction = Direction.NEUTRAL, 0.0
        lead = "技术面和资金面都没有可计分的数，观望。"
    elif len(points) >= 2 and all(p > 0 for p in points):
        direction, conviction = Direction.STRONG_BUY, 1.0
        lead = "技术面和资金面同向偏多。"
    elif len(points) >= 2 and all(p < 0 for p in points):
        direction, conviction = Direction.STRONG_SELL, -1.0
        lead = "技术面和资金面同向偏空。"
    elif sum(points) > 0:
        direction, conviction = Direction.BUY, 0.5
        lead = "已有的一面偏多。"
    elif sum(points) < 0:
        direction, conviction = Direction.SELL, -0.5
        lead = "已有的一面偏空。"
    else:
        direction, conviction = Direction.NEUTRAL, 0.0
        lead = "已有的面没有方向。"
    text = " ".join([lead, *faces, *gaps, *side])
    return _bundle("trend", market, direction, conviction, text, "；".join(faces), gaps)


def _with_calls(bundle: RawBundle, calls: list[dict], model: str | None) -> RawBundle:
    if calls:
        bundle.meta = {"calls": calls}
    if model:
        bundle.llm_model = model
    return bundle


async def research_signal(market: MarketData, pack: str, runner, model: str | None) -> RawBundle:
    if runner is None or not model:
        return _abstain("research", market, "未调用模型，研究信号弃权")
    prompt = (
        "你只根据下面的证据摘要做评级。缺失的均线、资金流、财务、新闻、社交不能写成事实。"
        "投研备忘录里已经写成缺失的商业模式、竞争、风险不能补成事实。"
        "rating 只能是 buy、overweight、hold、underweight、sell。\n\n"
        f"{pack}"
    )
    try:
        result, meta = await runner.run_json(
            "research", model, prompt, _Rating, output_schema=_SCHEMA,
        )
    except Exception as exc:
        return _abstain("research", market, f"研究信号失败: {str(exc)[:160]}")
    mapped = _RATING_MAP.get(str(result.rating).strip().lower())
    if mapped is None:
        return _abstain("research", market, f"研究信号评级无法识别: {result.rating}")
    direction, conviction = mapped
    bundle = _bundle(
        "research", market, direction, conviction, result.analysis,
        "技术面；资金面；基本面；新闻；社交", [],
    )
    usage = getattr(meta, "usage", None) if meta is not None else None
    thread_id = getattr(meta, "thread_id", None) if meta is not None else None
    return _with_calls(bundle, [{"agent": "research", "thread_id": thread_id, "usage": usage}], model)


async def value_signal(market: MarketData, runner, model: str | None, *, trace_dir=None) -> RawBundle:
    run = await run_workflow(market, runner, model, trace_dir=trace_dir)
    faces = "财务"
    if run.abstain_reason or run.rating is None:
        bundle = _abstain("value", market, run.abstain_reason or "价值信号弃权", faces)
        bundle.texts["analysis"] = run.memo
        for gap in (run.role_gaps or ROLE_GAPS):
            if gap not in bundle.data_gaps:
                bundle.data_gaps.append(gap)
        return _with_calls(bundle, run.calls, model)
    mapped = _RATING_MAP.get(run.rating)
    if mapped is None:
        bundle = _abstain("value", market, f"价值信号评级无法识别: {run.rating}", faces)
        bundle.texts["analysis"] = run.memo
        return _with_calls(bundle, run.calls, model)
    direction, conviction = mapped
    return _with_calls(
        _bundle("value", market, direction, conviction, run.memo, faces, list(run.role_gaps or ROLE_GAPS)),
        run.calls, model,
    )


async def build_signals(market: MarketData, runner, model: str | None, *, trace_dir=None) -> list[RawBundle]:
    value = await value_signal(market, runner, model, trace_dir=trace_dir)
    pack = f"{render_pack(market)}\n\n## 投研备忘录\n{value.texts.get('analysis', gap_memo())}"
    return [
        trend_signal(market),
        await research_signal(market, pack, runner, model),
        value,
    ]


def to_engine_signal(bundle: RawBundle) -> EngineSignal:
    return EngineSignal(
        signal_id=make_signal_id(bundle.engine, bundle.ticker, bundle.as_of, seed=bundle.report_ref),
        engine=bundle.engine,
        raw_report_ref=bundle.report_ref,
        data_sources=bundle.data_sources,
        llm_model=bundle.llm_model,
        ticker=bundle.ticker,
        market=bundle.market,
        as_of=bundle.as_of,
        direction=bundle.direction or Direction.NEUTRAL,
        conviction=bundle.conviction if bundle.direction is not None else 0.0,
        reasoning=bundle.texts.get("analysis", ""),
        degraded=bundle.data_status == "insufficient_data",
        data_status=bundle.data_status,
        data_gaps=list(bundle.data_gaps),
        quality_notes=bundle.texts.get("faces") or None,
    )


def render_signals(signals) -> str:
    lines = ["## 三份信号"]
    for sig in signals:
        gaps = "；".join(sig.data_gaps) if sig.data_gaps else "无"
        lines += [
            f"### {sig.engine}",
            f"- 方向: {sig.direction.value}",
            f"- 把握: {sig.conviction:+.2f}",
            f"- 数据状态: {sig.data_status}",
            f"- 用到的面: {sig.quality_notes or '见正文'}",
            f"- 缺失: {gaps}",
            sig.reasoning or "",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"
