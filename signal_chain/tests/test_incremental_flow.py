from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from signal_chain.config import NormTicker
from signal_chain.data.layer import load
from signal_chain.data.models import Fact, FilingExcerpt
from signal_chain.data.underlying_store import CATEGORIES, evidence_rows

DAY = datetime.now(ZoneInfo("America/New_York")).date()
STAMP = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)


class EvidenceStore:
    def __init__(self, *, fail_read=False, fail_save=False):
        self.fail_read = fail_read
        self.fail_save = fail_save
        self.records = {category: [] for category in CATEGORIES}
        self.states = {}
        self.writes = []

    def read(self, ticker):
        if self.fail_read:
            raise RuntimeError("supabase offline")
        return self.records, self.states

    def save(self, ticker, category, records, error=None):
        if self.fail_save:
            raise RuntimeError("supabase write offline")
        self.writes.append((category, records, error))
        self.records[category].extend({**record, "category": category} for record in records)
        self.states[category] = {"last_attempt": datetime.now(timezone.utc).isoformat(),
                                 "last_success": datetime.now(timezone.utc).isoformat() if records else None}


def _get(url, headers=None):
    if "company_tickers" in url:
        return {"0": {"ticker": "TEST", "title": "Test Inc", "cik_str": 123}}
    if "companyfacts" in url:
        return {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
            {"form": "10-K", "val": 100.0, "start": "2024-01-01",
             "end": "2024-12-31", "filed": "2025-02-10"}]}}}}}
    if "submissions" in url:
        return {"filings": {"recent": {"form": ["10-K"], "filingDate": ["2025-02-10"],
                                       "accessionNumber": ["0000000123-25-000001"],
                                       "primaryDocument": ["report.htm"]}}}
    if "calendar/earnings" in url:
        return {"data": {"rows": []}}
    raise AssertionError(url)


def _run(store, get=_get, *, slow_only=True):
    return load(NormTicker("US", "TEST"), DAY, object(), include_chain=False,
                evidence_store=store, keys={}, get=get, get_text=lambda *_args: "",
                quota=lambda: False, slow_only=slow_only, fetch_macro=lambda: [],
                futu_probe=lambda *_args: (None, "offline"))


def test_first_load_persists_and_next_load_reuses_slow_evidence():
    store = EvidenceStore()
    first = _run(store)
    assert first.evidence_persisted
    assert first.snapshot.fundamentals.status == "available"
    assert any(category == "fundamentals" and records for category, records, _ in store.writes)
    assert len(store.records["company"]) == 1
    second = _run(store)
    assert second.snapshot.fundamentals.status == "available"
    assert any(row.id == "supabase" and row.field == "fundamentals" for row in second.sources)


def test_unavailable_store_never_authorizes_research_evidence():
    for store in (EvidenceStore(fail_read=True), EvidenceStore(fail_save=True)):
        result = _run(store)
        assert not result.evidence_persisted
        assert result.snapshot.fundamentals.status == "available"
        assert any(row.field == "evidence" and row.state == "missing" for row in result.sources)


def test_failed_refresh_keeps_old_version_but_never_promotes_it():
    store = EvidenceStore()
    _run(store)
    store.states["fundamentals"] = {
        "last_attempt": datetime.now(timezone.utc).isoformat(),
        "last_success": "2026-08-01T00:00:00Z", "last_error": "SEC unavailable",
    }
    writes = len(store.writes)
    result = _run(store, get=lambda url, headers=None: (_ for _ in ()).throw(RuntimeError("offline")))
    assert not result.evidence_persisted
    assert len(store.writes) == writes
    assert any(row.id == "supabase" and row.field == "fundamentals" and
               row.state == "stale" for row in result.sources)


def test_failed_company_refresh_keeps_cik_for_context_only():
    store = EvidenceStore()
    _run(store)
    store.states["company"] = {"last_attempt": datetime.now(timezone.utc).isoformat(),
                               "last_success": "2026-08-01T00:00:00Z", "last_error": "SEC down"}
    result = _run(store)
    assert not result.evidence_persisted
    assert result.snapshot.fundamentals.status == "available"


def test_single_source_fallback_cannot_qualify_as_persisted_research():
    store = EvidenceStore()

    def fallback(url, headers=None):
        if "company_tickers" in url:
            return _get(url, headers)
        if "companyfacts" in url:
            raise RuntimeError("SEC offline")
        if "income-statement" in url:
            return [{"revenue": 123, "date": "2025-12-31"}]
        return _get(url, headers)

    result = load(NormTicker("US", "TEST"), DAY, object(), include_chain=False,
                  evidence_store=store, keys={"FMP_API_KEY": "test"}, get=fallback,
                  get_text=lambda *_args: "", quota=lambda: True, slow_only=True,
                  futu_probe=lambda *_args: (None, "offline"))
    assert result.snapshot.fundamentals.status == "available"
    assert not result.evidence_persisted
