"""下次财报日。Nasdaq 日历为主，Finnhub 近月日历补预期。"""

from __future__ import annotations

from datetime import date, timedelta


def nasdaq_url(day: date) -> str:
    return f"https://api.nasdaq.com/api/calendar/earnings?date={day.isoformat()}"


def finnhub_url(symbol: str, start: date, end: date, token: str) -> str:
    return (
        "https://finnhub.io/api/v1/calendar/earnings"
        f"?from={start.isoformat()}&to={end.isoformat()}&symbol={symbol}&token={token}"
    )


def nasdaq_hit(payload, symbol: str) -> dict | None:
    rows = ((payload or {}).get("data") or {}).get("rows") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, dict) and str(row.get("symbol") or "").upper() == symbol.upper():
            return row
    return None


def finnhub_next(payload, symbol: str) -> dict | None:
    rows = payload.get("earningsCalendar") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return None
    hits = [
        row for row in rows
        if isinstance(row, dict) and str(row.get("symbol") or "").upper() == symbol.upper() and row.get("date")
    ]
    if not hits:
        return None
    return min(hits, key=lambda row: str(row["date"]))


def estimate_note(row: dict | None) -> str:
    if not row:
        return ""
    parts = []
    when = row.get("date")
    hour = row.get("hour")
    if when:
        parts.append(f"Finnhub {when} {hour or ''}".strip())
    eps = row.get("epsEstimate")
    revenue = row.get("revenueEstimate")
    if eps is not None:
        parts.append(f"EPS预期 {eps}")
    if revenue is not None:
        parts.append(f"营收预期 {revenue}")
    return "；".join(parts)


def upcoming_days(start: date, count: int = 24) -> list[date]:
    return [start + timedelta(days=offset) for offset in range(count)]
