"""Financial Modeling Prep。报价兜底和美股营收。Basic 套餐每天 250 次。"""

from __future__ import annotations

import json
import threading
from datetime import date
from pathlib import Path

from ..config import REPO_ROOT

STATE_PATH = REPO_ROOT / "signal_chain" / ".data_state.json"
DAILY_LIMIT = 250
_BASE = "https://financialmodelingprep.com/stable"
_QUOTA_LOCK = threading.Lock()


def take_quota(today: date, path: Path = STATE_PATH, limit: int = DAILY_LIMIT) -> bool:
    with _QUOTA_LOCK:
        data: dict = {}
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
        key = f"fmp:{today.isoformat()}"
        used = int(data.get(key) or 0)
        if used >= limit:
            return False
        data[key] = used + 1
        path.write_text(json.dumps(data), encoding="utf-8")
        return True


def endpoint(path: str, key: str, **params: str) -> str:
    query = "&".join(f"{name}={value}" for name, value in params.items())
    return f"{_BASE}/{path}?{query}&apikey={key}"


def note(payload) -> str | None:
    if not isinstance(payload, dict):
        return None
    text = payload.get("Error Message") or payload.get("error") or payload.get("message")
    return str(text)[:200] if text else None


def _records(payload) -> list | None:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and not note(payload):
        for name in ("historical", "data"):
            rows = payload.get(name)
            if isinstance(rows, list):
                return rows
    return None


def _float(raw) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value != value:
        return None
    return value


def daily_probe(payload) -> dict | None:
    """收成 underlying_fetch 能吃的 quote/kline。"""
    rows = _records(payload)
    if not rows:
        return None
    bars = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        close = _float(row.get("close"))
        open_ = _float(row.get("open"))
        day = str(row.get("date") or "")[:10]
        if close is None or open_ is None or len(day) < 10:
            continue
        high = _float(row.get("high"))
        low = _float(row.get("low"))
        volume = _float(row.get("volume"))
        bars.append({
            "trade_date": day,
            "open": open_,
            "high": high if high is not None else open_,
            "low": low if low is not None else open_,
            "close": close,
            "volume": volume,
        })
    if not bars:
        return None
    bars.sort(key=lambda item: item["trade_date"])
    last = bars[-1]
    return {
        "quote": {"last": last["close"], "session_date": last["trade_date"], "error": None},
        "kline": {"adjusted": False, "bars": bars, "error": None},
    }


def revenue_ttm(payload) -> float | None:
    rows = _records(payload)
    if not rows or not isinstance(rows[0], dict):
        return None
    return _float(rows[0].get("revenue"))


def _dated_revenue(payload, label) -> tuple[float, str] | None:
    rows = _records(payload)
    if not rows or not isinstance(rows[0], dict):
        return None
    value = _float(rows[0].get("revenue"))
    day = str(rows[0].get("date") or "")[:10]
    if value is None or len(day) < 10:
        return None
    return value, f"{label}{day}"


def annual_revenue(payload) -> tuple[float, str, str] | None:
    """年报营收、FY 标签、报告期结束日。"""
    parsed = _dated_revenue(payload, "")
    if parsed is None:
        return None
    value, day = parsed
    return value, f"FY{day[:4]}", day


def quarter_revenue(payload) -> tuple[float, str] | None:
    """最近一季营收，期间用报告期结束日。"""
    return _dated_revenue(payload, "Q")


def public_error(exc: BaseException) -> str:
    import re
    text = re.sub(r"apikey=[^&\s'\"]+", "apikey=***", str(exc))
    if "402" in text or "Restricted Endpoint" in text:
        return "当前套餐不含该接口"
    return text[:160]


def headlines(payload, limit: int = 3) -> str | None:
    rows = _records(payload) or []
    titles = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if title:
            titles.append(title)
        if len(titles) >= limit:
            break
    return "；".join(titles) or None
