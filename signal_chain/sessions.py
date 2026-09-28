"""美股交易日。运行日不是开盘日时，用 NYSE 上一场。

正规开盘前，当天的日线还不存在。只有请求日就是美东今天、且早于 9:30，才再退回上一场。
历史交易日不看墙上的钟。
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

_ET = ZoneInfo("America/New_York")
_OPEN = time(9, 30)


def _calendar():
    import exchange_calendars as xcals

    return xcals.get_calendar("XNYS")


def nyse_session(day: date) -> date:
    import pandas as pd

    cal = _calendar()
    ts = pd.Timestamp(day)
    if cal.is_session(ts):
        return day
    return cal.date_to_session(ts, direction="previous").date()


def _previous_session(day: date) -> date:
    return nyse_session(day - timedelta(days=1))


def _as_et(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=_ET)
    return moment.astimezone(_ET)


def _before_open(moment: datetime) -> bool:
    return _as_et(moment).time() < _OPEN


def session_for(market: str, day: date, now: datetime | None = None) -> date:
    if market != "US":
        return day
    session = nyse_session(day)
    moment = _as_et(now) if now is not None else datetime.now(_ET)
    if day == moment.date() and session == day and _before_open(moment):
        return _previous_session(day)
    return session


def quote_session(update_time: str) -> date | None:
    """报价刷新时间归到它所属的那场。开盘前的时间戳用上一场，不拿日历日当交易日。"""
    text = str(update_time or "").strip()
    if len(text) < 19 or text.lower() in {"nat", "nan", "none"}:
        return None
    bare = text[:26].replace("T", " ")
    try:
        parsed = datetime.fromisoformat(bare)
    except ValueError:
        return None
    moment = _as_et(parsed)
    return session_for("US", moment.date(), now=moment)


def align_futu_quote(payload: dict | None) -> dict | None:
    """有 update_time 时，用它覆盖快照里的报价交易日。"""
    if not payload:
        return payload
    quote = payload.get("quote")
    if not isinstance(quote, dict) or not quote.get("update_time"):
        return payload
    session = quote_session(str(quote["update_time"]))
    if session is None:
        return payload
    return {**payload, "quote": {**quote, "session_date": session.isoformat()}}
