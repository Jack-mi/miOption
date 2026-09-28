"""Cboe 延迟期权链。Futu 不可用时的免费兜底。"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

from ..config import NormTicker, Settings
from ..schema import ChainSnapshot, OptionRow


def options_url(symbol: str) -> str:
    return f"https://cdn-api.cboe.com/api/global/delayed_quotes/options/{symbol}.json"


def _num(raw) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value


def _int(raw) -> int | None:
    value = _num(raw)
    return None if value is None else int(value)


def parse_chain(payload, t: NormTicker, as_of: date, window_days: int) -> ChainSnapshot:
    data = (payload or {}).get("data") or {}
    rows = data.get("options")
    if not isinstance(rows, list):
        raise ValueError("Cboe 无 options")
    pattern = re.compile(rf"^{re.escape(t.code)}(\d{{6}})([CP])(\d{{8}})$")
    horizon = as_of + timedelta(days=window_days)
    out: list[OptionRow] = []
    for row in rows:
        match = pattern.match(str(row.get("option") or ""))
        if not match:
            continue
        ymd, cp, strike = match.groups()
        expiry = date(2000 + int(ymd[:2]), int(ymd[2:4]), int(ymd[4:]))
        if not as_of <= expiry <= horizon:
            continue
        out.append(OptionRow(
            code=row["option"],
            strike=int(match.group(3)) / 1000,
            expiry=expiry,
            option_type="CALL" if cp == "C" else "PUT",
            bid=_num(row.get("bid")),
            ask=_num(row.get("ask")),
            last=_num(row.get("last_trade_price")),
            iv=_num(row.get("iv")),
            delta=_num(row.get("delta")),
            open_interest=_int(row.get("open_interest")),
            volume=_int(row.get("volume")),
        ))
    if not out:
        raise ValueError("Cboe 窗口内无合约")
    return ChainSnapshot(
        ticker=t.canonical, market=t.market, as_of=as_of,
        fetched_at=datetime.now(timezone.utc), source="cboe",
        spot=_num(data.get("current_price")), rows=out,
        degraded=True, notes="Cboe delayed quotes",
    )


def fetch_chain(t: NormTicker, trade_date: date, settings: Settings, get) -> ChainSnapshot:
    payload = get(options_url(t.code))
    return parse_chain(payload, t, trade_date, int(settings.chain["expiry_window_days"]))
