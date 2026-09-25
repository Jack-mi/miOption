"""基本面只在两源对得上时可用；没有披露日就不写财报催化剂。"""

from datetime import date, datetime, timezone

import pytest

from signal_chain.options.underlying_fetch import build_snapshot
from signal_chain.research.berkshire import attach_fundamentals, earnings_catalyst, note_earnings

D0 = date(2026, 9, 23)
NOW = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)


def _snap():
    return build_snapshot(
        ticker="US.AAPL", market="US", trade_date=D0, fetched_at=NOW,
        futu_error="未探测", yahoo_error="未探测",
    )


def test_one_source_stays_missing():
    snap = attach_fundamentals(
        _snap(), metric="revenue", period="FY2025", values={"sec": 100.0},
        as_of=D0, fetched_at=NOW,
    )
    assert snap.fundamentals.status == "missing"
    assert "第二个" in (snap.fundamentals.error or "")


def test_two_sources_within_one_percent_are_available():
    snap = attach_fundamentals(
        _snap(), metric="revenue", period="FY2025",
        values={"sec": 100.0, "macrotrends": 100.5},
        as_of=D0, fetched_at=NOW,
    )
    assert snap.fundamentals.status == "available"
    assert snap.fundamentals.period == "FY2025"
    assert "sec" in (snap.fundamentals.source or "")
    assert snap.fundamentals.error is None


def test_two_sources_over_one_percent_stay_missing():
    snap = attach_fundamentals(
        _snap(), metric="revenue", period="FY2025",
        values={"sec": 100.0, "macrotrends": 103.0},
        as_of=D0, fetched_at=NOW,
    )
    assert snap.fundamentals.status == "missing"
    assert "1%" in (snap.fundamentals.error or "")


def test_earnings_date_requires_source_and_skips_when_absent():
    snap = _snap()
    assert note_earnings(snap, None, source=None) is snap
    assert earnings_catalyst(snap) is None
    with pytest.raises(ValueError):
        note_earnings(snap, D0, source=None)
    noted = note_earnings(snap, date(2026, 10, 29), source="sec 8-K")
    cat = earnings_catalyst(noted)
    assert cat is not None
    assert cat.type == "earnings"
    assert cat.expected_date == date(2026, 10, 29)
    assert cat.description == "sec 8-K"
