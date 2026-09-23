"""TradingAgents 产物适配：state.json -> RawBundle。

评级映射（方案锁定）：
Buy -> (BUY, +1.0) / Overweight -> (BUY, +0.5) / Hold -> (NEUTRAL, 0)
Underweight -> (SELL, -0.5) / Sell -> (SELL, -1.0) / REVIEW -> 作废。
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ..config import NormTicker
from ..schema import Direction
from .base import RawBundle

_RATING_MAP: dict[str, tuple[Direction, float]] = {
    "buy": (Direction.BUY, 1.0),
    "overweight": (Direction.BUY, 0.5),
    "hold": (Direction.NEUTRAL, 0.0),
    "underweight": (Direction.SELL, -0.5),
    "sell": (Direction.SELL, -1.0),
}

_SECTION_KEYS = [
    "final_trade_decision",
    "trader_investment_plan",
    "market_report",
    "fundamentals_report",
    "sentiment_report",
    "news_report",
    "investment_plan",
    "risk_debate_state",
]


class TaAdapter:
    engine = "tradingagents"

    def __init__(self, data_sources: list[str] | None = None):
        self.data_sources = data_sources or ["yfinance", "sec_edgar", "stockstats"]

    def load(self, state_path: Path, t: NormTicker, as_of: date,
             llm_model: str | None = None) -> RawBundle:
        with open(state_path, encoding="utf-8") as f:
            state = json.load(f)

        rating = str(state.get("rating") or "").strip().lower()
        mapped = _RATING_MAP.get(rating)
        direction, conviction = mapped if mapped else (None, 0.0)

        sections = state.get("sections") or {}
        texts: dict[str, str] = {}
        for key in _SECTION_KEYS:
            val = sections.get(key)
            if isinstance(val, str) and val.strip():
                texts[key] = val
            elif isinstance(val, dict):
                texts[key] = json.dumps(val, ensure_ascii=False)[:6000]

        return RawBundle(
            engine=self.engine,
            ticker=t.canonical,
            market=t.market,
            as_of=as_of,
            report_ref=str(state_path),
            direction=direction,
            conviction=conviction,
            data_sources=list(self.data_sources),
            engine_version=None,
            llm_model=llm_model,
            texts=texts,
            meta={"rating": state.get("rating"), "ta_ticker": state.get("ticker")},
        )
