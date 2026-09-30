"""Supabase evidence ledger for slow-moving US research data; no account or live quotes."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from ..schema.underlying import FieldMeta
from . import macro
from .http import get_json, post_json
from .models import Fact, FilingExcerpt, Ratio, SourceRow

CATEGORIES = ("company", "fundamentals", "filing", "earnings")
INTERVALS = {"company": timedelta(days=30), "fundamentals": timedelta(days=7), "filing": timedelta(days=7),
             "earnings": timedelta(days=1)}


def _clock(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def record(item_key: str, source: str, source_at: date | datetime, payload: dict,
           fetched_at: datetime, quality: str = "verified") -> dict:
    observed = source_at.isoformat() if isinstance(source_at, datetime) else datetime.combine(
        source_at, datetime.min.time(), timezone.utc).isoformat()
    return {"item_key": item_key, "source": source, "source_at": observed,
            "fetched_at": fetched_at.isoformat(), "quality": quality,
            "payload": payload, "digest": _digest(payload)}


class UnderlyingStore:
    def __init__(self, key: str, *, get=get_json, post=post_json):
        self.key = key
        self.get = get
        self.post = post

    def read(self, ticker: str) -> tuple[dict[str, list[dict]], dict[str, dict]]:
        if not self.key:
            raise RuntimeError("missing SUPABASE_SERVICE_ROLE_KEY")
        headers = macro._headers(self.key)
        base = macro.SUPABASE_URL + "/rest/v1/"
        evidence: dict[str, list[dict]] = {category: [] for category in CATEGORIES}
        offset = 0
        while True:
            query = urlencode({"ticker": f"eq.{ticker}",
                               "select": "category,item_key,source,source_at,fetched_at,quality,payload,digest",
                               "order": "id.asc", "limit": "1000", "offset": str(offset)})
            page = self.get(base + "underlying_evidence?" + query, headers)
            if not isinstance(page, list):
                raise ValueError("invalid evidence response")
            for row in page:
                if row.get("category") in evidence:
                    evidence[row["category"]].append(row)
            if len(page) < 1000:
                break
            offset += len(page)
        states = self.get(base + "underlying_refresh?" + urlencode({"ticker": f"eq.{ticker}",
                          "select": "category,last_attempt,last_success,last_error"}), headers)
        if not isinstance(states, list):
            raise ValueError("invalid refresh response")
        return evidence, {row["category"]: row for row in states}

    def save(self, ticker: str, category: str, records: list[dict], error: str | None = None) -> None:
        if category not in CATEGORIES:
            raise ValueError(category)
        self.post(macro.SUPABASE_URL + "/rest/v1/rpc/save_underlying_evidence",
                  macro._headers(self.key), {"input_ticker": ticker, "input_category": category,
                                            "input_records": records, "input_error": error})


def current(records: list[dict], *, day: date | None = None) -> list[dict]:
    def known_by(row: dict) -> bool:
        observed = _clock(row.get("source_at"))
        fetched = _clock(row.get("fetched_at"))
        if not observed or not fetched or row.get("quality") != "verified":
            return False
        if day is None:
            return True
        observed_day = (observed.astimezone(ZoneInfo("America/New_York")).date()
                        if row.get("category") in {"company", "earnings"} else observed.date())
        return observed_day <= day and fetched.astimezone(ZoneInfo("America/New_York")).date() <= day

    eligible = [row for row in records if known_by(row)]
    selected = {}
    for row in eligible:
        key = row["item_key"]
        previous = selected.get(key)
        ordering = lambda item: (_clock(item["fetched_at"]),
                                 item.get("source") == "nasdaq" if row.get("category") == "earnings" else False,
                                 _clock(item["source_at"]))
        if previous is None or ordering(row) > ordering(previous):
            selected[key] = row
    return list(selected.values())


def due(category: str, state: dict | None, records: list[dict], now: datetime,
        *, day: date | None = None) -> bool:
    attempt = _clock((state or {}).get("last_attempt"))
    success = _clock((state or {}).get("last_success"))
    chosen = current(records, day=day)
    if attempt and timedelta(0) <= now - attempt < timedelta(minutes=15):
        return False
    if not chosen:
        return True
    if success is None or success > now:
        return True
    if category == "earnings":
        event = chosen[0]["payload"].get("date")
        if not event or date.fromisoformat(event) < (day or now.date()):
            return True
        interval = timedelta(hours=6) if date.fromisoformat(event) <= (day or now.date()) + timedelta(days=10) else INTERVALS[category]
    else:
        interval = INTERVALS[category]
    return now - success >= interval


def usable(category: str, state: dict | None, records: list[dict], now: datetime,
           *, day: date | None = None) -> bool:
    if (state or {}).get("last_error") or not current(records, day=day):
        return False
    success = _clock((state or {}).get("last_success"))
    if not success or success > now:
        return False
    return not due(category, {**state, "last_attempt": None}, records, now, day=day)


def facts_from(records: list[dict], day: date) -> tuple[list[Fact], list[Ratio], FieldMeta]:
    chosen = current(records, day=day)
    facts = [Fact(**{key: value for key, value in row["payload"].items() if key != "kind"})
             for row in chosen if row["payload"].get("kind") == "fact"]
    ratios = [Ratio(**row["payload"]["value"]) for row in chosen if row["payload"].get("kind") == "ratio"]
    latest = max((row for row in chosen if row["payload"].get("metric") == "revenue"),
                 key=lambda row: (row["payload"]["period"], row["source"] == "edgar",
                                  _clock(row["source_at"])), default=None)
    if latest is None:
        return facts, ratios, FieldMeta(status="missing", error="无有效历史财务证据")
    return facts, ratios, FieldMeta(status="available", source=latest["source"],
                                   as_of=_clock(latest["source_at"]).date(),
                                   fetched_at=_clock(latest["fetched_at"]),
                                   period=latest["payload"]["period"])


def excerpts_from(records: list[dict], day: date) -> list[FilingExcerpt]:
    return [FilingExcerpt(section=row["payload"]["section"], text=row["payload"]["text"],
                          source=row["source"], as_of=date.fromisoformat(row["source_at"][:10]),
                          quality=row["payload"].get("quality", ""))
            for row in current(records, day=day)]


def earnings_from(records: list[dict], day: date) -> tuple[date | None, str | None]:
    choices = [row for row in current(records, day=day) if row["payload"].get("date")]
    if not choices:
        return None, None
    latest = max(choices, key=lambda row: (_clock(row["fetched_at"]), row["source"] == "nasdaq"))
    event = date.fromisoformat(latest["payload"]["date"])
    return (event, latest["source"]) if event >= day else (None, None)


def evidence_rows(category: str, data, fetched_at: datetime) -> list[dict]:
    if category == "fundamentals":
        facts, ratios = data
        rows = [record(f"{fact.source}:{fact.metric}:{fact.period}", fact.source,
                       date.fromisoformat(fact.filed), {"kind": "fact", **fact.__dict__}, fetched_at)
                for fact in facts if fact.source == "edgar" and fact.period and fact.filed]
        filed = [date.fromisoformat(fact.filed) for fact in facts if fact.filed]
        if filed:
            rows.extend(record(f"ratio:{ratio.metric}:{ratio.period}", "edgar", max(filed),
                               {"kind": "ratio", "value": ratio.__dict__}, fetched_at)
                        for ratio in ratios if ratio.source == "edgar")
        return rows
    if category == "company":
        company = data
        return [record("identity", "edgar", fetched_at, company, fetched_at)] if company else []
    if category == "filing":
        return [record(item.section, item.source, item.as_of,
                       {"section": item.section, "text": item.text, "quality": item.quality}, fetched_at)
                for item in data if item.as_of and item.source == "edgar" and item.text]
    if category == "earnings":
        when, source = data
        return [record("next_earnings", source, fetched_at,
                       {"date": when.isoformat(), "time_basis": "observed_at_fetch"}, fetched_at)] if when and source else []
    return []


def used(category: str, records: list[dict]) -> SourceRow:
    return SourceRow("supabase", category, "used", f"复用 {len(records)} 条历史证据，来源时点未改写")
