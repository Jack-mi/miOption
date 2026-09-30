from datetime import date, datetime, timedelta, timezone

from signal_chain.data.daily_store import DailyStore
from signal_chain.data.layer import _completed_bars, _completed_session, _history_start
from signal_chain.options.underlying_fetch import build_snapshot
from zoneinfo import ZoneInfo


def test_daily_bars_incremental_and_revision_history(tmp_path):
    store = DailyStore(tmp_path / "bars.sqlite")
    assert store.path.stat().st_mode & 0o777 == 0o600
    day = date(2026, 9, 28)
    original = {"trade_date": day.isoformat(), "open": 10, "close": 11}
    revision = {**original, "close": 12}
    incomplete = {"trade_date": (day + timedelta(days=1)).isoformat(), "close": 13}
    store.save("US.TEST", "futu", True, [original, incomplete], day)
    store.save("US.TEST", "futu", True, [original, revision], day)
    assert store.read("US.TEST", "futu", True, day) == [revision]
    assert store.read("US.TEST", "futu", False, day) == []
    assert store.read("US.TEST", "futu", True, day - timedelta(days=1)) == []


def test_completed_session_does_not_skip_yesterday_premarket():
    et = ZoneInfo("America/New_York")
    monday = date(2026, 9, 28)
    assert _completed_session(monday, datetime(2026, 9, 29, 8, tzinfo=et)) == monday
    assert _completed_session(monday, datetime(2026, 9, 28, 10, tzinfo=et)) == date(2026, 9, 25)
    assert _completed_session(monday, datetime(2026, 9, 28, 17, tzinfo=et)) == monday


def test_intraday_snapshot_uses_only_previous_completed_bars():
    et = ZoneInfo("America/New_York")
    monday = date(2026, 9, 28)
    friday = date(2026, 9, 25)
    bars = [{"trade_date": (friday - timedelta(days=offset)).isoformat(),
             "open": 100, "close": 100} for offset in (4, 3, 2, 1, 0)]
    snapshot = build_snapshot(ticker="US.TEST", market="US", trade_date=monday,
                              fetched_at=datetime(2026, 9, 28, 10, tzinfo=et),
                              futu={"kline": {"adjusted": True, "bars": bars}},
                              kline_session=friday)
    assert snapshot.kline.meta.status == "available"
    assert snapshot.kline.meta.as_of == friday
    assert snapshot.technical.meta.status == "available"


def test_missing_completed_session_rewinds_history_start():
    monday = date(2026, 9, 28)
    records = [{"trade_date": day} for day in ("2026-09-23", "2026-09-25", "2026-09-28")]
    assert _history_start(records, monday, monday) == date(2026, 9, 17)
    assert _history_start(records + [{"trade_date": "2026-09-24"}], monday, monday) == date(2026, 9, 21)


def test_fallback_eod_excludes_unfinished_daily_bar():
    probe = {"quote": {"last": 12}, "kline": {"adjusted": False, "bars": [
        {"trade_date": "2026-09-25", "close": 11},
        {"trade_date": "2026-09-28", "close": 12}]}}
    completed = _completed_bars(probe, date(2026, 9, 25))
    assert completed["kline"]["bars"] == [probe["kline"]["bars"][0]]
    assert completed["quote"] == probe["quote"]
