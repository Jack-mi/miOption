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


def _state_url() -> str:
    return f"{SUPABASE_URL}/rest/v1/rpc/record_macro_refresh"


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
    state_error = None
    try:
        states = get(f"{SUPABASE_URL}/rest/v1/macro_refresh_state?select=series,last_attempt,last_success,last_error",
                     _headers(api_key))
        if not isinstance(states, list):
            raise ValueError("宏观刷新状态无效")
    except Exception as exc:
        states = []
        state_error = str(exc)[:160]
    note = "；".join(f"{p.series} 观测 {p.as_of.isoformat()}" for p in points)
    fetched = [str(row.get("fetched_at") or "") for row in payload if isinstance(row, dict)]
    if fetched:
        note += "；获取 " + ",".join(sorted(set(fetched)))
    failures = [f"{row['series']}: {row['last_error']}" for row in states
                if row.get("last_error")]
    if failures:
        note += "；刷新失败 " + "；".join(failures)
    state_by_series = {row["series"]: row for row in states if isinstance(row, dict) and row.get("series")}
    missing = [point.series for point in points if point.series not in state_by_series]
    if missing:
        note += "；尚无刷新状态 " + ",".join(missing)
    successes = [f"{point.series} {state_by_series[point.series]['last_success']}"
                 for point in points if point.series in state_by_series and
                 state_by_series[point.series].get("last_success")]
    if successes:
        note += "；最近刷新 " + "；".join(successes)
    rows = [SourceRow("supabase", "macro", "used", note)]
    if state_error:
        rows.append(SourceRow("supabase", "macro_refresh_state", "missing", state_error))
    return points, rows


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
    state_rows: list[dict] = []
    attempted_at = datetime.now(timezone.utc).isoformat()
    for series, series_id in fred.SERIES:
        try:
            payload = get(fred.observations_url(series_id, fred_key))
            found = fred.latest(payload)
        except Exception as exc:
            reason = fred.public_error(exc)
            errors.append(f"{series}: {reason}")
            state_rows.append({"series": series, "last_attempt": attempted_at, "last_error": reason})
            continue
        if found is None:
            errors.append(f"{series}: 无观测")
            state_rows.append({"series": series, "last_attempt": attempted_at, "last_error": "无观测"})
            continue
        points.append(MacroPoint(series, found[0], found[1], "fred"))

    try:
        if points:
            post(_upsert_url(), {**_headers(supabase_key), "Prefer": "resolution=merge-duplicates"},
                 [
                {
                    "series": p.series,
                    "as_of": p.as_of.isoformat(),
                    "value": p.value,
                    "source": p.source,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
                for p in points
                 ])
            state_rows.extend({"series": p.series, "last_attempt": attempted_at,
                               "last_success": attempted_at, "last_error": None} for p in points)
        if state_rows:
            post(_state_url(), _headers(supabase_key), {"input_rows": state_rows})
    except Exception as exc:
        return points, [SourceRow("supabase", "macro_refresh", "missing", str(exc)[:160])]
    if not points:
        return [], [SourceRow("fred", "macro_refresh", "missing", "；".join(errors) or "无观测")]

    note = "；".join(f"{p.series} {p.as_of.isoformat()}" for p in points)
    if errors:
        note += "；失败 " + "；".join(errors)
    return points, [SourceRow("supabase", "macro_refresh", "missing" if errors else "used", note)]
