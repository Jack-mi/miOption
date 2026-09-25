"""标的日级快照。价格只在 status=available 时保留；缺数、过期、错币种不能当成已取到。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

FieldStatus = Literal["available", "missing", "unsupported", "stale"]


class FieldMeta(BaseModel):
    status: FieldStatus
    source: str | None = None
    as_of: date | None = None
    fetched_at: datetime | None = None
    timezone: str | None = None
    error: str | None = None
    period: str | None = None


class QuoteField(BaseModel):
    meta: FieldMeta
    currency: Literal["USD", "HKD"] | None = None
    last: float | None = None


class DailyBar(BaseModel):
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


class KlineField(BaseModel):
    meta: FieldMeta
    adjusted: bool | None = None
    bars: list[DailyBar] = Field(default_factory=list)


class TechnicalField(BaseModel):
    meta: FieldMeta
    indicators: dict[str, float] = Field(default_factory=dict)


def _unsupported(label: str) -> FieldMeta:
    return FieldMeta(status="unsupported", error=f"本轮不接入{label}")


class UnderlyingSnapshot(BaseModel):
    ticker: str
    market: Literal["US", "HK"]
    currency: Literal["USD", "HKD"]
    as_of: date
    fetched_at: datetime
    quote: QuoteField
    kline: KlineField
    technical: TechnicalField
    capital_flow: FieldMeta = Field(default_factory=lambda: _unsupported("资金流"))
    fundamentals: FieldMeta = Field(default_factory=lambda: _unsupported("基本面"))
    news: FieldMeta = Field(default_factory=lambda: _unsupported("新闻"))
    earnings_date: date | None = None
    earnings_source: str | None = None

    @model_validator(mode="after")
    def _contract(self) -> UnderlyingSnapshot:
        expected = "USD" if self.market == "US" else "HKD"
        if self.currency != expected:
            raise ValueError(f"币种 {self.currency} 与市场 {self.market} 不一致")
        self._check_quote()
        self._check_kline()
        self._check_technical()
        self._check_sourced("资金流", self.capital_flow, require_period=False)
        self._check_sourced("新闻", self.news, require_period=False)
        self._check_sourced("基本面", self.fundamentals, require_period=True)
        if self.earnings_date is not None and not self.earnings_source:
            raise ValueError("财报日缺少出处")
        return self

    def _check_sourced(self, label: str, meta: FieldMeta, *, require_period: bool) -> None:
        if meta.status != "available":
            return
        if not meta.source or meta.fetched_at is None or meta.as_of is None:
            raise ValueError(f"{label} available 缺少 source 或时点")
        if require_period and not meta.period:
            raise ValueError(f"{label} available 缺少期间")

    def _check_quote(self) -> None:
        meta = self.quote.meta
        if self.quote.currency and self.quote.currency != self.currency:
            raise ValueError("报价币种与快照币种不一致")
        if meta.status == "available":
            if self.quote.last is None:
                raise ValueError("报价 available 但缺少 last")
            if meta.as_of != self.as_of:
                raise ValueError("报价交易日与快照 as_of 不一致")
            if not meta.source or meta.fetched_at is None:
                raise ValueError("报价缺少 source 或 fetched_at")
        elif self.quote.last is not None:
            raise ValueError("非 available 报价不得携带价格")

    def _check_kline(self) -> None:
        meta = self.kline.meta
        if meta.status == "available":
            if not self.kline.bars:
                raise ValueError("日线 available 但缺少 K 线")
            last = self.kline.bars[-1].trade_date
            if meta.as_of != last:
                raise ValueError("日线 as_of 与最后一根 K 线不一致")
            if last > self.as_of or (self.as_of - last).days > 4:
                raise ValueError("日线最后交易日不在运行日的可接受窗口内")
            if self.kline.adjusted is None:
                raise ValueError("日线 available 但未标明是否复权")
            if not meta.source or meta.fetched_at is None:
                raise ValueError("日线缺少 source 或 fetched_at")
        elif self.kline.bars:
            raise ValueError("非 available 日线不得携带 K 线")

    def _check_technical(self) -> None:
        meta = self.technical.meta
        if meta.status == "available":
            if not self.technical.indicators:
                raise ValueError("技术指标 available 但没有指标值")
            if meta.as_of is None or meta.as_of > self.as_of or (self.as_of - meta.as_of).days > 4:
                raise ValueError("技术指标交易日不在运行日的可接受窗口内")
        elif self.technical.indicators:
            raise ValueError("非 available 技术指标不得携带数值")

    def critical_gaps(self) -> list[str]:
        """报价或日线不是 available 时的弃权原因。技术指标不单独否决。"""
        gaps: list[str] = []
        for label, meta in (("报价", self.quote.meta), ("日线", self.kline.meta)):
            if meta.status != "available":
                detail = meta.error or meta.status
                gaps.append(f"{label} {meta.status}: {detail}")
        return gaps
