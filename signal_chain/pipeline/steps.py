"""流水线步骤：RawBundle -> EngineSignal -> EnsembleSignal -> 链摘要 -> 策略。

LLM 只出现在标注 [CODEX] 的步骤；其余全是确定性代码。
"""

from __future__ import annotations

import json

from ..adapters import RawBundle
from ..agents.codex import AgentFailed, AgentMeta, CodexAgentRunner
from ..agents.prompts import (
    EXTRACTION_OUTPUT_SCHEMA,
    STRATEGY_OUTPUT_SCHEMA,
    SYNTHESIS_OUTPUT_SCHEMA,
    ExtractionResult,
    StrategyResult,
    SynthesisResult,
    extraction_prompt,
    strategy_prompt,
    synthesis_prompt,
)
from ..schema import (
    Catalyst,
    ChainSnapshot,
    EngineSignal,
    EnsembleSignal,
    PriceMap,
    StrategyProposal,
    make_signal_id,
)


def build_chain_digest(chain: ChainSnapshot, per_expiry: int = 6, max_expiries: int = 8) -> str:
    """把链压缩成策略 agent 可读的摘要：前 max_expiries 个到期日各取 spot 附近合约。"""
    if chain.spot is None:
        return "（链无 spot，无法摘要）"
    all_exp = chain.expiries()
    lines = [
        f"spot={chain.spot} source={chain.source}",
        f"全部到期日: {', '.join(str(e) for e in all_exp)}",
    ]
    for exp in all_exp[:max_expiries]:
        near = sorted(
            (r for r in chain.rows if r.expiry == exp),
            key=lambda r: abs(r.strike - chain.spot),
        )[:per_expiry]
        atm = chain.atm_iv(exp)
        lines.append(f"## {exp} (ATM IV={atm:.1%})" if atm else f"## {exp}")
        for r in sorted(near, key=lambda r: (r.strike, r.option_type)):
            sp = f"{r.spread_pct:.0%}" if r.spread_pct is not None else "n/a"
            iv = f"{r.iv:.0%}" if r.iv else "n/a"
            lines.append(
                f"  {r.code} {r.option_type} K={r.strike} bid={r.bid} ask={r.ask} "
                f"iv={iv} oi={r.open_interest} vol={r.volume} spread={sp} delta={r.delta}"
            )
    return "\n".join(lines)


async def extract_signal(
    runner: CodexAgentRunner,
    bundle: RawBundle,
    model: str,
) -> tuple[EngineSignal, AgentMeta | None]:
    """[CODEX] 抽取非确定性字段 + 确定性字段组装 EngineSignal。"""
    base = dict(
        signal_id=make_signal_id(bundle.engine, bundle.ticker, bundle.as_of,
                                 seed=bundle.report_ref),
        engine=bundle.engine,
        engine_version=bundle.engine_version,
        raw_report_ref=bundle.report_ref,
        data_sources=bundle.data_sources,
        llm_model=bundle.llm_model,
        ticker=bundle.ticker,
        market=bundle.market,
        as_of=bundle.as_of,
        direction=bundle.direction,
        conviction=bundle.conviction,
    )
    try:
        result, meta = await runner.run_json(
            f"extract:{bundle.engine}", model,
            extraction_prompt(bundle.engine, bundle.ticker, bundle.as_of, bundle.texts),
            ExtractionResult,
            output_schema=EXTRACTION_OUTPUT_SCHEMA,
        )
        signal = EngineSignal(
            **base,
            reasoning=result.reasoning,
            risk_flags=result.risk_flags,
            catalysts=[Catalyst(**c.model_dump()) for c in result.catalysts],
            price_map=PriceMap(**result.price_map.model_dump()),
            horizon_days=result.horizon_days,
            volatility_view=result.volatility_view,
            quality_notes=result.quality_notes,
        )
        return signal, meta
    except AgentFailed as exc:
        fallback_text = " ".join(bundle.texts.values())[:500]
        signal = EngineSignal(
            **base,
            reasoning=f"[抽取降级] {fallback_text}",
            degraded=True,
            quality_notes=f"extraction agent 失败: {exc}",
        )
        return signal, None


async def synthesize_notes(
    runner: CodexAgentRunner,
    ensemble: EnsembleSignal,
    model: str,
) -> tuple[EnsembleSignal, AgentMeta | None]:
    """[CODEX] 只写 synthesis_notes / dissent_summary，其余字段不动。"""
    components = [
        {"engine": c.engine, "direction": c.direction.value,
         "conviction": c.conviction, "reasoning": c.reasoning}
        for c in ensemble.components
    ]
    try:
        result, meta = await runner.run_json(
            "synthesize", model,
            synthesis_prompt(ensemble.ticker, ensemble.agreement, components),
            SynthesisResult,
            output_schema=SYNTHESIS_OUTPUT_SCHEMA,
        )
        return ensemble.model_copy(update={
            "synthesis_notes": result.synthesis_notes,
            "dissent_summary": result.dissent_summary,
        }), meta
    except AgentFailed:
        return ensemble.model_copy(update={
            "synthesis_notes": "[合成说明降级] agent 失败，仅保留规则合成结果"
        }), None


async def propose_strategies(
    runner: CodexAgentRunner,
    ensemble: EnsembleSignal,
    chain: ChainSnapshot,
    model: str,
) -> tuple[list[StrategyProposal], str | None, AgentMeta | None]:
    """[CODEX] 策略选结构。返回 (proposals, decline_reason, meta)。"""
    signal_json = ensemble.model_dump_json(exclude={"components"})[:4000]
    digest = build_chain_digest(chain)
    try:
        result, meta = await runner.run_json(
            "strategy", model,
            strategy_prompt(signal_json, digest),
            StrategyResult,
            output_schema=STRATEGY_OUTPUT_SCHEMA,
        )
        proposals = [StrategyProposal(**p.model_dump()) for p in result.proposals]
        return proposals, result.decline_reason, meta
    except AgentFailed as exc:
        return [], f"strategy agent 失败: {exc}", None
