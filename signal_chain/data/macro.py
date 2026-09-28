"""共享宏观层：Supabase 只读快照 + FRED 定时刷新。"""

from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Any

from ..data import fred
from ..data.models import MacroPoint, SourceRow
from .http import get_json, post_json

SUPABASE_PROJECT_REF = "gkchcblxtonfsthfgmbc"
SUPABASE_URL = os.environ.get("SUPABASE_URL", f"https://{SUPABASE_PROJECT_REF}.supabase.co")


def _headers(api_key: str) -> dict[str, str]:
    return {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _latest_url() -> str:
    return f"{SUPABASE_URL}/rest/v1/macro_latest?select=series,as_of,value,source,fetched_at"


def _upsert_url() -> str:
    return f"{SUPABASE_URL}/rest/v1/macro_observations"


def read_macro(api_key: str | None, get=get_json) -> tuple[list[MacroPoint], list[SourceRow]]:
    if not api_key:
        return [], [SourceRow("supabase", "macro", "missing", "没有 SUPABASE_SERVICE_ROLE_KEY")]
    try:
        payload = get(_latest_url(), _headers(api_key))
        points = _parse_latest(payload)
    except Exception as exc:
        return [], [SourceRow("supabase", "macro", "missing", str(exc)[:160])]
    if not points:
        return [], [SourceRow("supabase", "macro", "missing", "宏观快照为空")]
    note = "；".join(f"{p.series} {p.as_of.isoformat()}" for p in points)
    return points, [SourceRow("supabase", "macro", "used", note)]


def _parse_latest(payload: Any) -> list[MacroPoint]:
    if not isinstance(payload, list):
        return []
    out: list[MacroPoint] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        series = row.get("series")
        as_of = row.get("as_of")
        value = row.get("value")
        if not series or not as_of or value is None:
            continue
        try:
            out.append(MacroPoint(
                series=str(series),
                as_of=date.fromisoformat(str(as_of)[:10]),
                value=float(value),
                source=str(row.get("source") or "supabase"),
            ))
        except (TypeError, ValueError):
            continue
    return out


def refresh_macro(
    fred_key: str | None,
    supabase_key: str | None,
    *,
    get=get_json,
    post=post_json,
) -> tuple[list[MacroPoint], list[SourceRow]]:
    if not fred_key:
        return [], [SourceRow("fred", "macro_refresh", "missing", "没有 FRED_API_KEY")]
    if not supabase_key:
        return [], [SourceRow("supabase", "macro_refresh", "missing", "没有 SUPABASE_SERVICE_ROLE_KEY")]

    points: list[MacroPoint] = []
    errors: list[str] = []
    for series, series_id in fred.SERIES:
        try:
            payload = get(fred.observations_url(series_id, fred_key))
            found = fred.latest(payload)
        except Exception as exc:
            errors.append(f"{series}: {fred.public_error(exc)}")
            continue
        if found is None:
            errors.append(f"{series}: 无观测")
            continue
        points.append(MacroPoint(series, found[0], found[1], "fred"))

    if not points:
        return [], [SourceRow("fred", "macro_refresh", "missing", "；".join(errors) or "无观测")]

    try:
        post(
            _upsert_url(),
            {**_headers(supabase_key), "Prefer": "resolution=merge-duplicates"},
            [
                {
                    "series": p.series,
                    "as_of": p.as_of.isoformat(),
                    "value": p.value,
                    "source": p.source,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
                for p in points
            ],
        )
    except Exception as exc:
        return points, [SourceRow("supabase", "macro_refresh", "missing", str(exc)[:160])]

    note = "；".join(f"{p.series} {p.as_of.isoformat()}" for p in points)
    if errors:
        note += "；失败 " + "；".join(errors)
    return points, [SourceRow("supabase", "macro_refresh", "used", note)]
