"""证据摘要。研究环节一次看完卡片和全部切片。"""

from __future__ import annotations

from ..data.context import card, slice
from ..data.models import MarketData

_PACK = (
    "quote", "kline", "sma", "flow", "chain",
    "fundamentals", "earnings", "filing",
    "news", "social", "events",
    "business", "competition", "risk", "governance",
    "macro",
)


def render_pack(market: MarketData) -> str:
    return "\n".join([card(market), *(slice(market, name) for name in _PACK)])
