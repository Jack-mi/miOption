"""Nasdaq 历史日线。免费兜底，不需要 key。"""

from __future__ import annotations

from datetime import date, datetime


def historical_url(symbol: str, start: date, end: date) -> str:
    return (
        "https://api.nasdaq.com/api/quote/"
        f"{symbol}/historical?assetclass=stocks"
        f"&fromdate={start.isoformat()}&limit=30&todate={end.isoformat()}"
    )


def _num(raw) -> float | None:
    try:
        value = float(str(raw).replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return None
    return value


def daily_probe(payload) -> dict | None:
    """收成 underlying_fetch 能吃的 quote/kline。"""
    rows = ((payload or {}).get("data") or {}).get("tradesTable", {}).get("rows")
    if not isinstance(rows, list) or not rows:
        return None
    bars = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            day = datetime.strptime(str(row.get("date")), "%m/%d/%Y").date()
        except ValueError:
            continue
        close = _num(row.get("close"))
        open_ = _num(row.get("open"))
        if close is None or open_ is None:
            continue
        high = _num(row.get("high"))
        low = _num(row.get("low"))
        volume = _num(row.get("volume"))
        bars.append({
            "trade_date": day.isoformat(),
            "open": open_,
            "high": high if high is not None else open_,
            "low": low if low is not None else open_,
            "close": close,
            "volume": None if volume is None else int(volume),
        })
    if not bars:
        return None
    bars.sort(key=lambda row: row["trade_date"])
    return {
        "quote": {"last": bars[-1]["close"], "session_date": bars[-1]["trade_date"], "error": None},
        "kline": {"adjusted": False, "bars": bars, "error": None},
    }


def public_error(exc: BaseException) -> str:
    return str(exc)[:160]
