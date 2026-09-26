"""流水线步骤：合成说明。LLM 只在这一步出现，其余全是确定性代码。"""

from __future__ import annotations

from ..agents.llm import AgentFailed, AgentMeta, LlmRunner
from ..agents.prompts import SYNTHESIS_OUTPUT_SCHEMA, SynthesisResult, synthesis_prompt
from ..schema import EnsembleSignal


async def synthesize_notes(
    runner: LlmRunner,
    ensemble: EnsembleSignal,
    model: str,
) -> tuple[EnsembleSignal, AgentMeta | None]:
    """只写 synthesis_notes / dissent_summary，其余字段不动。"""
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
