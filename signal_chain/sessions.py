"""美股交易日。运行日不是开盘日时，用 NYSE 上一场。"""

from __future__ import annotations

from datetime import date


def nyse_session(day: date) -> date:
    import exchange_calendars as xcals
    import pandas as pd

    cal = xcals.get_calendar("XNYS")
    ts = pd.Timestamp(day)
    if cal.is_session(ts):
        return day
    return cal.date_to_session(ts, direction="previous").date()


def session_for(market: str, day: date) -> date:
    if market != "US":
        return day
    return nyse_session(day)
