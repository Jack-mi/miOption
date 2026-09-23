"""Codex agent 的 prompt 模板与请求/响应模型。"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class ExtractionCatalyst(BaseModel):
    type: str = "other"
    expected_date: date | None = None
    description: str


class ExtractionPriceMap(BaseModel):
    support: float | None = None
    resistance: float | None = None
    target: float | None = None
    invalid_below: float | None = None


class ExtractionResult(BaseModel):
    """抽取 agent 只负责这些非确定性字段；方向/强度等由适配器确定性计算。"""

    reasoning: str = ""
    risk_flags: list[str] = Field(default_factory=list)
    catalysts: list[ExtractionCatalyst] = Field(default_factory=list)
    price_map: ExtractionPriceMap = Field(default_factory=ExtractionPriceMap)
    horizon_days: tuple[int, int] = (3, 20)
    volatility_view: Literal["rising", "falling", "neutral", "unknown"] = "unknown"
    quality_notes: str | None = None

    @field_validator("volatility_view", mode="before")
    @classmethod
    def _norm_vol(cls, v):
        return str(v).lower() if isinstance(v, str) else v


EXTRACTION_OUTPUT_SCHEMA = ExtractionResult.model_json_schema()


def extraction_prompt(engine: str, ticker: str, as_of: date, texts: dict[str, str]) -> str:
    sections = "\n\n".join(
        f"## 报告段: {name}\n{content[:6000]}" for name, content in texts.items() if content
    )
    return f"""你是金融报告信息抽取器。以下是分析引擎 {engine} 对 {ticker}（分析日 {as_of}）的原始报告段落。

{sections}

# 任务
只输出一个 JSON 对象，字段：
- reasoning: 中文，200 字内，概括该引擎观点的核心论据（含资金面/基本面/技术面要点，有什么写什么）
- risk_flags: 字符串数组，报告明确提到的风险条目，逐条原文压缩
- catalysts: 数组，未来事件催化剂 {{type: earnings/product/policy/litigation/other, expected_date: YYYY-MM-DD 或 null, description}}
- price_map: {{support, resistance, target, invalid_below}}，报告提到的关键价位，数字或 null
- horizon_days: [最短, 最长] 整数对，该观点的有效期估计（日级波段默认 [3,20]）
- volatility_view: rising/falling/neutral/unknown，报告对波动率走向的判断，没提就 unknown
- quality_notes: 数据缺失/异常的说明，无则 null

不要输出任何 JSON 之外的内容。报告里没有的信息保持空值，禁止编造数字和日期。"""


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


class StrategyLegOut(BaseModel):
    """策略腿输出：容错大小写与 action/side 别名（kimi-k3 实测会变体）。"""

    model_config = ConfigDict(populate_by_name=True)

    code: str
    option_type: Literal["CALL", "PUT"]
    strike: float
    expiry: date
    side: Literal["buy", "sell"] = Field(validation_alias=AliasChoices("side", "action"))
    quantity: int = 1

    @field_validator("option_type", mode="before")
    @classmethod
    def _norm_option_type(cls, v):
        return str(v).upper() if isinstance(v, str) else v

    @field_validator("side", mode="before")
    @classmethod
    def _norm_side(cls, v):
        return str(v).lower() if isinstance(v, str) else v


class StrategyProposalOut(BaseModel):
    name: str
    thesis: str
    legs: list[StrategyLegOut]
    max_loss: float | None = None
    max_profit: float | None = None
    net_premium: float | None = None
    is_short_vol: bool = False
    notes: str | None = None


class StrategyResult(BaseModel):
    proposals: list[StrategyProposalOut] = Field(default_factory=list)
    decline_reason: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_leg_shaped_proposals(cls, data):
        """容错：模型把腿平铺成 proposal 时（缺 name/thesis/legs），归拢为一个结构。"""
        if not isinstance(data, dict):
            return data
        props = data.get("proposals")
        if not isinstance(props, list):
            return data
        leg_shaped = [p for p in props if isinstance(p, dict) and "legs" not in p and "code" in p]
        if leg_shaped and len(leg_shaped) == len(props):
            data = dict(data)
            data["proposals"] = [{
                "name": "未命名结构（模型输出已归拢）",
                "thesis": leg_shaped[0].get("note") or leg_shaped[0].get("thesis") or "",
                "legs": props,
            }]
        return data


STRATEGY_OUTPUT_SCHEMA = StrategyResult.model_json_schema()


def strategy_prompt(signal_json: str, chain_digest: str) -> str:
    return f"""你是期权策略师。基于下面的合成信号与期权链摘要，给出 0~3 个候选期权结构。

# 合成信号
{signal_json}

# 期权链摘要（按到期日分组，spot 附近行权价，iv/oi/volume/spread_pct 已算出）
{chain_digest}

# 规则
- 只做风险可定义的结构（价差/备兑/保护），禁止裸卖期权
- 腿必须来自链摘要里的真实合约（code 原样引用），禁止编造合约
- 每条腿的字段名严格为：code / option_type / strike / expiry / side / quantity；
  option_type 必须大写 CALL 或 PUT；side 必须小写 buy 或 sell；禁止用 action、call、long/short 等变体
- 方向与信号一致；信号为 neutral 或你不确定时，proposals 留空并填 decline_reason
- 每个结构给出 max_loss / max_profit / net_premium（正=净收入）与 is_short_vol 标记
- thesis 用中文说明结构与信号、催化剂、波动率的关系，100 字内

# 输出格式示例（结构必须长这样：proposals 的每一项是一个完整结构，legs 是它的腿数组）
{{"proposals": [{{"name": "牛市看涨价差", "thesis": "……", "legs": [{{"code": "合约代码", "option_type": "CALL", "strike": 340.0, "expiry": "2026-10-02", "side": "buy", "quantity": 1}}], "max_loss": 150.0, "max_profit": 100.0, "net_premium": -150.0, "is_short_vol": false, "notes": null}}], "decline_reason": null}}

不要输出 JSON 之外的内容。"""
