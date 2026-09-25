"""投研模型调用。Claude Agent SDK 只负责会话，请求只发到 DeepSeek 官方接口。"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from ..config import REPO_ROOT

T = TypeVar("T", bound=BaseModel)

MODEL = "deepseek-flash"
BASE_URL = "https://api.deepseek.com/anthropic"
_ENV_FILE = REPO_ROOT / ".env"
_BLOCKED_TOOLS = [
    "Bash", "Read", "Edit", "Write", "Agent", "WebSearch", "WebFetch", "Skill",
]


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


def load_deepseek_key() -> str:
    if os.environ.get("DEEPSEEK_API_KEY"):
        return os.environ["DEEPSEEK_API_KEY"]
    if not _ENV_FILE.exists():
        return ""
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        name, value = text.split("=", 1)
        if name.strip() == "DEEPSEEK_API_KEY":
            return value.strip().strip('"').strip("'")
    return ""


def assemble_call(prompt: str, *, model: str, api_key: str) -> dict[str, Any]:
    """组装一次无工具调用。密钥只进环境变量。"""
    if api_key and api_key in prompt:
        raise AgentFailed("密钥不能进入提示词")
    return {
        "model": model or MODEL,
        "tools": [],
        "allowed_tools": [],
        "prompt": prompt,
        "env": {
            "ANTHROPIC_BASE_URL": BASE_URL,
            "ANTHROPIC_API_KEY": api_key,
        },
    }


def extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise AgentFailed(f"响应中无 JSON 对象: {text[:200]}")
    return json.loads(text[start:end + 1])


def _text_from_message(message) -> str:
    content = getattr(message, "content", None)
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        piece = getattr(block, "text", None)
        if piece:
            parts.append(piece)
    return "".join(parts)


class LlmRunner:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = load_deepseek_key() if api_key is None else api_key

    async def __aenter__(self) -> "LlmRunner":
        return self

    async def __aexit__(self, *exc) -> None:
        return None

    def _options(self, model: str):
        from claude_agent_sdk import ClaudeAgentOptions

        spec = assemble_call("", model=model, api_key=self.api_key)
        return ClaudeAgentOptions(
            model=spec["model"],
            tools=[],
            allowed_tools=[],
            disallowed_tools=list(_BLOCKED_TOOLS),
            permission_mode="dontAsk",
            strict_mcp_config=True,
            mcp_servers={},
            max_turns=1,
            env=spec["env"],
            system_prompt="你只根据用户给出的材料回答。不要调用工具，不要读取文件，不要联网。",
        )

    async def _complete(self, agent: str, model: str, prompt: str) -> tuple[str, AgentMeta]:
        from claude_agent_sdk import AssistantMessage, ResultMessage, query

        if not self.api_key:
            raise AgentFailed("没有 DEEPSEEK_API_KEY")
        assemble_call(prompt, model=model, api_key=self.api_key)
        meta = AgentMeta(agent=agent, model=model or MODEL)
        text = ""
        t0 = time.monotonic()
        async for message in query(prompt=prompt, options=self._options(meta.model)):
            if isinstance(message, AssistantMessage):
                text = _text_from_message(message) or text
                if message.session_id:
                    meta.thread_id = message.session_id
                if message.usage:
                    meta.usage = message.usage
            elif isinstance(message, ResultMessage):
                meta.thread_id = message.session_id or meta.thread_id
                if message.usage:
                    meta.usage = message.usage
                if message.is_error:
                    raise AgentFailed((message.result or "模型调用失败")[:300])
                if message.result:
                    text = message.result
        meta.elapsed_ms = int((time.monotonic() - t0) * 1000)
        return text, meta

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
        schema_note = ""
        if output_schema is not None:
            schema_note = "\n\n只输出一个 JSON 对象，字段必须符合这个 schema：\n" + json.dumps(
                output_schema, ensure_ascii=False,
            )
        meta = AgentMeta(agent=agent, model=model or MODEL)
        last_err = ""
        for attempt in range(1, retries + 2):
            meta.attempts = attempt
            full = prompt + schema_note
            if last_err:
                full += f"\n\n# 上次输出未通过校验，请修正后重新输出完整 JSON\n{last_err}"
            try:
                text, step = await self._complete(agent, model, full)
            except AgentFailed as exc:
                last_err = str(exc)[:600]
                continue
            meta.thread_id = step.thread_id
            meta.usage = step.usage
            meta.elapsed_ms += step.elapsed_ms
            try:
                return response_model.model_validate(extract_json(text)), meta
            except (json.JSONDecodeError, ValidationError, AgentFailed) as exc:
                last_err = f"{type(exc).__name__}: {str(exc)[:600]}"
        raise AgentFailed(f"{agent} 连续 {meta.attempts} 次输出校验失败: {last_err}")

    async def run_text(self, agent: str, model: str, prompt: str) -> AgentResult:
        text, meta = await self._complete(agent, model, prompt)
        meta.attempts = 1
        return AgentResult(meta=meta, text=text)
