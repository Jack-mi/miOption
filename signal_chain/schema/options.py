"""期权链快照与策略结构 schema。"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class OptionRow(BaseModel):
    code: str
    strike: float
    expiry: date
    option_type: Literal["CALL", "PUT"]
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    iv: float | None = None          # 小数（0.35 = 35%）
    delta: float | None = None
    open_interest: int | None = None
    volume: int | None = None

    @property
    def mid(self) -> float | None:
        if self.bid and self.ask and self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2
        return self.last

    @property
    def spread_pct(self) -> float | None:
        m = self.mid
        if m and m > 0 and self.bid is not None and self.ask is not None:
            return (self.ask - self.bid) / m
        return None


class ChainSnapshot(BaseModel):
    ticker: str                       # 归一格式
    market: Literal["US", "HK", "CN"]
    as_of: date
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: Literal["futu", "yfinance"]
    spot: float | None = None
    rows: list[OptionRow] = Field(default_factory=list)
    degraded: bool = False
    notes: str | None = None

    def expiries(self) -> list[date]:
        return sorted({r.expiry for r in self.rows})

    def atm_iv(self, expiry: date, n: int = 3) -> float | None:
        """该到期日最接近 spot 的 n 个合约 IV 均值。"""
        if self.spot is None:
            return None
        near = sorted(
            (r for r in self.rows if r.expiry == expiry and r.iv and r.iv > 0),
            key=lambda r: abs(r.strike - self.spot),
        )[:n]
        if not near:
            return None
        return sum(r.iv for r in near if r.iv) / len(near)


class StrategyLeg(BaseModel):
    code: str
    option_type: Literal["CALL", "PUT"]
    strike: float
    expiry: date
    side: Literal["buy", "sell"]
    quantity: int = 1


class StrategyProposal(BaseModel):
    name: str                          # e.g. "bull_put_spread"
    thesis: str                        # 与信号的关联说明
    legs: list[StrategyLeg]
    max_loss: float | None = None      # 每单位最大亏损（由校验层按链上价格复核）
    max_profit: float | None = None
    net_premium: float | None = None   # 正=净收入(credit)，负=净支出(debit)
    is_short_vol: bool = False         # 净卖出权利金/负 vega 结构
    notes: str | None = None


class RiskDecision(BaseModel):
    approved: bool
    vetoes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
