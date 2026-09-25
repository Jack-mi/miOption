"""统一 Signal schema v0.1（面向期权决策）。pydantic 校验即契约。"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Direction(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


VolatilityView = Literal["rising", "falling", "neutral", "unknown"]
Agreement = Literal["aligned", "partial", "conflicted", "single_source", "insufficient_data"]
DataStatus = Literal["actionable", "opinion", "insufficient_data"]


class Catalyst(BaseModel):
    type: str  # earnings / product / policy / litigation / other
    expected_date: date | None = None
    description: str


class PriceMap(BaseModel):
    support: float | None = None
    resistance: float | None = None
    target: float | None = None
    invalid_below: float | None = None  # 观点失效位


def make_signal_id(engine: str, ticker: str, as_of: date, seed: str) -> str:
    h = hashlib.sha1(seed.encode()).hexdigest()[:8]
    return f"{engine}-{ticker}-{as_of.isoformat()}-{h}"


class EngineSignal(BaseModel):
    # 身份与溯源
    signal_id: str
    engine: str  # tradingagents / dsa
    engine_version: str | None = None
    raw_report_ref: str
    data_sources: list[str] = Field(default_factory=list)
    llm_model: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # 标的与时间口径
    ticker: str  # US.AAPL / HK.00700 / CN.600519
    market: Literal["US", "HK", "CN"]
    as_of: date
    # 核心观点
    direction: Direction
    conviction: float = Field(ge=-1.0, le=1.0)
    horizon_days: tuple[int, int] = (3, 20)
    reasoning: str = ""
    risk_flags: list[str] = Field(default_factory=list)
    # 期权决策增量视图
    volatility_view: VolatilityView = "unknown"
    catalysts: list[Catalyst] = Field(default_factory=list)
    price_map: PriceMap = Field(default_factory=PriceMap)
    # 质量元数据。insufficient_data 表示缺关键报价/日线，不能当完整一票。
    degraded: bool = False
    data_status: DataStatus = "actionable"
    data_gaps: list[str] = Field(default_factory=list)
    quality_notes: str | None = None


class EnsembleSignal(BaseModel):
    ticker: str
    market: Literal["US", "HK", "CN"]
    as_of: date
    components: list[EngineSignal]
    agreement: Agreement
    direction: Direction
    conviction: float = Field(ge=-1.0, le=1.0)
    volatility_view: VolatilityView = "unknown"
    catalysts: list[Catalyst] = Field(default_factory=list)
    synthesis_notes: str = ""
    dissent_summary: str | None = None
    quality_notes: str | None = None
