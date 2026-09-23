"""Codex SDK agent 运行器。

约定（方案 v5）：
- 所有 agent thread 一律 Sandbox.read_only —— LLM 不碰文件系统；
- 结构化输出优先用 SDK 原生 output_schema，再用 pydantic 复核；
- 失败重试 1 次（把校验错误喂回去），再失败抛 AgentFailed，由上层降级；
- thread id / usage / 耗时记入 meta，供 runs/ 台账审计。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, TypeVar

from openai_codex import AsyncCodex, Sandbox
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class AgentFailed(RuntimeError):
    pass


@dataclass
class AgentMeta:
    agent: str
    model: str
    thread_id: str | None = None
    usage: dict[str, Any] | None = None
    elapsed_ms: int = 0
    attempts: int = 0


@dataclass
class AgentResult:
    meta: AgentMeta
    text: str


def extract_json(text: str) -> dict:
    """从 final_response 里提取 JSON 对象（容错前后散文）。"""
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise AgentFailed(f"响应中无 JSON 对象: {text[:200]}")
    return json.loads(text[start:end + 1])


class CodexAgentRunner:
    def __init__(self) -> None:
        self._codex: AsyncCodex | None = None

    async def __aenter__(self) -> "CodexAgentRunner":
        self._codex = AsyncCodex()
        await self._codex.__aenter__()
        return self

    async def __aexit__(self, *exc) -> None:
        if self._codex is not None:
            await self._codex.__aexit__(*exc)
            self._codex = None

    async def run_json(
        self,
        agent: str,
        model: str,
        prompt: str,
        response_model: type[T],
        *,
        output_schema: dict | None = None,
        retries: int = 1,
    ) -> tuple[T, AgentMeta]:
        """跑一个 JSON 输出 agent，pydantic 校验，失败重试。"""
        assert self._codex is not None, "use as async context manager"
        meta = AgentMeta(agent=agent, model=model)
        last_err = ""
        for attempt in range(1, retries + 2):
            meta.attempts = attempt
            thread = await self._codex.thread_start(model=model, sandbox=Sandbox.read_only)
            meta.thread_id = getattr(thread, "id", None)
            full_prompt = prompt if not last_err else (
                f"{prompt}\n\n# 上次输出未通过校验，请修正后重新输出完整 JSON\n{last_err}"
            )
            t0 = time.monotonic()
            result = await thread.run(full_prompt, output_schema=output_schema)
            meta.elapsed_ms += int((time.monotonic() - t0) * 1000)
            usage = result.usage
            meta.usage = usage if isinstance(usage, dict) else (
                usage.model_dump() if usage is not None else None
            )
            if result.error:
                last_err = f"agent error: {result.error}"
                continue
            try:
                payload = extract_json(result.final_response or "")
                return response_model.model_validate(payload), meta
            except (json.JSONDecodeError, ValidationError, AgentFailed) as exc:
                last_err = f"{type(exc).__name__}: {str(exc)[:600]}"
        raise AgentFailed(f"{agent} 连续 {meta.attempts} 次输出校验失败: {last_err}")

    async def run_text(self, agent: str, model: str, prompt: str) -> AgentResult:
        """跑一个自由文本 agent（如 Reporter）。"""
        assert self._codex is not None, "use as async context manager"
        meta = AgentMeta(agent=agent, model=model, attempts=1)
        thread = await self._codex.thread_start(model=model, sandbox=Sandbox.read_only)
        meta.thread_id = getattr(thread, "id", None)
        t0 = time.monotonic()
        result = await thread.run(prompt)
        meta.elapsed_ms = int((time.monotonic() - t0) * 1000)
        if result.error:
            raise AgentFailed(f"{agent} error: {result.error}")
        return AgentResult(meta=meta, text=result.final_response or "")
