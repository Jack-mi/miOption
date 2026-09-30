from datetime import date, datetime, timedelta, timezone

from signal_chain.data.underlying_store import UnderlyingStore, current, due, evidence_rows, facts_from, record, usable
from signal_chain.data.models import Fact

NOW = datetime(2026, 9, 30, 14, 0, tzinfo=timezone.utc)


def test_revisions_and_freshness_keep_original_source_time():
    fact = Fact("edgar", "revenue", "FY2025", 100, "2026-01-31")
    original = evidence_rows("fundamentals", ([fact], []), NOW)[0]
    fact.value = 120
    revision = evidence_rows("fundamentals", ([fact], []), NOW + timedelta(days=2))[0]
    assert original["digest"] != revision["digest"]
    assert original["source_at"] == revision["source_at"]
    records = [{**row, "category": "fundamentals"} for row in (original, revision)]
    facts, _, meta = facts_from(records, (NOW + timedelta(days=2)).date())
    assert facts[0].value == 120
    assert meta.fetched_at == NOW + timedelta(days=2)
    assert facts_from(records, NOW.date())[0][0].value == 100
    state = {"last_attempt": NOW.isoformat(), "last_success": NOW.isoformat()}
    assert not due("fundamentals", state, records, NOW + timedelta(hours=2))
    assert due("fundamentals", state, records, NOW + timedelta(days=8))


def test_unverified_records_never_become_current():
    old = record("next_earnings", "finnhub", NOW, {"date": "2026-10-30"}, NOW,
                 quality="legacy_unverified")
    assert current([old]) == []
    assert due("earnings", None, [old], NOW)


def test_future_observation_and_fetch_cannot_look_ahead():
    before = record("next_earnings", "finnhub", NOW, {"date": "2026-10-30"}, NOW)
    after = record("next_earnings", "finnhub", NOW + timedelta(days=1),
                   {"date": "2026-10-31"}, NOW + timedelta(days=1))
    rows = [{**item, "category": "earnings"} for item in (before, after)]
    assert [row["payload"]["date"] for row in current(rows, day=NOW.date())] == ["2026-10-30"]
    assert not current(rows, day=NOW.date() - timedelta(days=1))


def test_failed_attempt_throttles_fetch_without_authorizing_cached_version():
    row = record("identity", "edgar", NOW, {"cik": "123"}, NOW)
    state = {"last_attempt": NOW.isoformat(), "last_success": (NOW - timedelta(days=40)).isoformat(),
             "last_error": "timeout"}
    assert not due("company", state, [row], NOW + timedelta(minutes=1))
    assert not usable("company", state, [row], NOW + timedelta(minutes=1))


def test_earnings_source_priority_breaks_same_fetch_time_ties():
    rows = [{**record("next_earnings", source, NOW, {"date": event}, NOW),
             "category": "earnings"} for source, event in
            (("nasdaq", "2026-10-29"), ("finnhub", "2026-10-30"))]
    from signal_chain.data.underlying_store import earnings_from

    assert earnings_from(rows, NOW.date()) == (date(2026, 10, 29), "nasdaq")


def test_expired_latest_earnings_does_not_revive_older_forecast():
    from signal_chain.data.underlying_store import earnings_from

    earlier = record("next_earnings", "nasdaq", NOW - timedelta(days=10),
                     {"date": "2026-11-10"}, NOW - timedelta(days=10))
    latest = record("next_earnings", "nasdaq", NOW, {"date": "2026-09-29"}, NOW)
    records = [{**row, "category": "earnings"} for row in (earlier, latest)]
    assert earnings_from(records, NOW.date()) == (None, None)


def test_store_reads_paginated_records_and_saves_atomic_rpc():
    calls = []

    def get(url, headers):
        calls.append(url)
        return []

    def post(url, headers, payload):
        calls.append((url, payload))

    store = UnderlyingStore("key", get=get, post=post)
    evidence, state = store.read("US.TEST")
    assert not state and not any(evidence.values())
    record_data = record("business", "edgar", date(2026, 9, 1), {"text": "business"}, NOW)
    store.save("US.TEST", "filing", [record_data])
    assert len(calls) == 3
    assert calls[-1][1]["input_records"] == [record_data]
