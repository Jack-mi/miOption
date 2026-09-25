"""Polymarket 只读已映射的事件。没有映射不猜测。"""

from __future__ import annotations

import json
from pathlib import Path

MAP_PATH = Path(__file__).with_name("events.json")


def load_map(path: Path = MAP_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in data.items() if v}


def prices(payload: dict | list) -> list[tuple[str, float]]:
    event = payload[0] if isinstance(payload, list) and payload else payload
    if not isinstance(event, dict):
        return []
    markets = event.get("markets") or []
    out = []
    for market in markets:
        name = str(market.get("question") or market.get("groupItemTitle") or "").strip()
        raw = market.get("outcomePrices") or market.get("lastTradePrice")
        if isinstance(raw, str) and raw.startswith("["):
            try:
                raw = json.loads(raw)[0]
            except (json.JSONDecodeError, IndexError):
                raw = None
        try:
            price = float(raw)
        except (TypeError, ValueError):
            continue
        if name:
            out.append((name, price))
    return out[:3]
