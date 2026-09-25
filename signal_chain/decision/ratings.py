"""研究信号和价值信号共用的评级表。"""

from __future__ import annotations

from ..schema import Direction

RATING_MAP: dict[str, tuple[Direction, float]] = {
    "buy": (Direction.BUY, 1.0),
    "overweight": (Direction.BUY, 0.5),
    "hold": (Direction.NEUTRAL, 0.0),
    "underweight": (Direction.SELL, -0.5),
    "sell": (Direction.SELL, -1.0),
}
