"""FRED 宏观观测。联邦基金利率、CPI、失业率各取最新一个有效点。"""

from __future__ import annotations

from datetime import date

SERIES = (
    ("FEDERAL_FUNDS_RATE", "DFF"),
    ("CPI", "CPIAUCSL"),
    ("UNEMPLOYMENT", "UNRATE"),
    ("DGS10", "DGS10"),
)


def observations_url(series_id: str, api_key: str) -> str:
    return (
        "https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}&api_key={api_key}&file_type=json"
        "&sort_order=desc&limit=5"
    )


def latest(payload) -> tuple[date, float] | None:
    rows = payload.get("observations") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw = str(row.get("value") or "")
        if raw in ("", "."):
            continue
        day = str(row.get("date") or "")[:10]
        try:
            return date.fromisoformat(day), float(raw)
        except (TypeError, ValueError):
            continue
    return None


def public_error(exc: BaseException) -> str:
    import re
    text = re.sub(r"api_key=[^&\s'\"]+", "api_key=***", str(exc))
    return text[:160]
