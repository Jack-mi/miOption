"""Alpha Vantage。报价兜底、美股财务第二源、新闻主源。每天 25 次。"""

from __future__ import annotations

import json
import threading
from datetime import date
from pathlib import Path

from ..config import REPO_ROOT

STATE_PATH = REPO_ROOT / "signal_chain" / ".data_state.json"
DAILY_LIMIT = 25
_QUOTA_LOCK = threading.Lock()


def take_quota(today: date, path: Path = STATE_PATH, limit: int = DAILY_LIMIT) -> bool:
    with _QUOTA_LOCK:
        data: dict = {}
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
        key = today.isoformat()
        used = int(data.get(key) or 0)
        if used >= limit:
            return False
        data[key] = used + 1
        path.write_text(json.dumps(data), encoding="utf-8")
        return True


def note(payload: dict) -> str | None:
    if not isinstance(payload, dict):
        return None
    text = payload.get("Note") or payload.get("Information") or payload.get("Error Message")
    return str(text)[:200] if text else None


def daily_probe(payload: dict) -> dict | None:
    """收成 underlying_fetch 能吃的 quote/kline。"""
    series = payload.get("Time Series (Daily)") or {}
    bars = []
    for day, row in series.items():
        try:
            close = float(row.get("4. close"))
            open_ = float(row.get("1. open"))
        except (TypeError, ValueError):
            continue
        bars.append({
            "trade_date": day[:10],
            "open": open_,
            "high": float(row.get("2. high") or open_),
            "low": float(row.get("3. low") or open_),
            "close": close,
            "volume": float(row["5. volume"]) if row.get("5. volume") else None,
        })
    if not bars:
        return None
    bars.sort(key=lambda item: item["trade_date"])
    last = bars[-1]
    return {
        "quote": {"last": last["close"], "session_date": last["trade_date"], "error": None},
        "kline": {"adjusted": True, "bars": bars, "error": None},
    }


def revenue_ttm(overview: dict) -> float | None:
    raw = overview.get("RevenueTTM")
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value != value:
        return None
    return value


def latest_indicator(payload: dict) -> tuple[date, float] | None:
    """经济序列取最新一个有数值的观测。限额或空序列返回 None。"""
    if not isinstance(payload, dict) or note(payload):
        return None
    best: tuple[date, float] | None = None
    for row in payload.get("data") or []:
        if not isinstance(row, dict):
            continue
        raw = row.get("value")
        if raw in (None, "", "."):
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        day = str(row.get("date") or "")[:10]
        if len(day) < 10:
            continue
        found = (date.fromisoformat(day), value)
        if best is None or found[0] > best[0]:
            best = found
    return best


def headlines(payload: dict, limit: int = 3) -> str | None:
    feed = payload.get("feed") or []
    titles = []
    for item in feed:
        title = str(item.get("title") or "").strip()
        if title:
            titles.append(title)
        if len(titles) >= limit:
            break
    return "；".join(titles) or None
