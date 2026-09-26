"""Claude Agent SDK 的 prompt 模板与请求/响应模型。请求只发到 DeepSeek。"""

from __future__ import annotations

from pydantic import BaseModel


class SynthesisResult(BaseModel):
    synthesis_notes: str = ""
    dissent_summary: str | None = None


SYNTHESIS_OUTPUT_SCHEMA = SynthesisResult.model_json_schema()


def synthesis_prompt(ticker: str, agreement: str, components: list[dict]) -> str:
    lines = "\n".join(
        f"- 引擎 {c['engine']}: 方向={c['direction']}, 强度={c['conviction']}, 论据={c['reasoning'][:300]}"
        for c in components
    )
    dissent_rule = (
        "本组合方向异号，dissent_summary 必填，说明分歧焦点。"
        if agreement == "conflicted"
        else "无实质分歧时 dissent_summary 为 null。"
    )
    return f"""你是信号合成员。{ticker} 的两个引擎信号如下，合成一致性判定为 {agreement}：

{lines}

# 任务
只输出一个 JSON 对象：
- synthesis_notes: 中文，150 字内，说明两源是否互相印证、各自的增量信息是什么
- dissent_summary: {dissent_rule}

不要输出 JSON 之外的内容。"""
