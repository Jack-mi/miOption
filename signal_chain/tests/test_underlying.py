"""标的快照契约：缺字段、过期、错币种、降级来源、脱敏账本。不访问 OpenD 或公网。"""

import json
from datetime import date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from signal_chain.options.underlying_fetch import build_snapshot, coverage_entry
from signal_chain.schema.underlying import (
    DividendField,
    FieldMeta,
    KlineField,
    QuoteField,
    TechnicalField,
    UnderlyingSnapshot,
    VolBasisField,
)
from signal_chain.storage import write_coverage

D0 = date(2026, 9, 23)
NOW = datetime(2026, 9, 23, 20, 0, tzinfo=timezone.utc)


def _bars(n=5, end=D0, price=100.0):
    rows = []
    for i in range(n):
        day = end - timedelta(days=n - 1 - i)
        px = price + i
        rows.append({
            "trade_date": day.isoformat(),
            "open": px, "high": px + 1, "low": px - 1, "close": px, "volume": 10,
        })
    return rows


def _fresh_probe(source_price=180.0):
    return {
        "quote": {"last": source_price, "session_date": D0.isoformat(), "error": None},
        "kline": {"adjusted": True, "bars": _bars(), "error": None},
    }


def _empty(**kw):
    missing = FieldMeta(status="missing", error="无")
    base = dict(
        ticker="US.AAPL", market="US", currency="USD", as_of=D0, fetched_at=NOW,
        quote=QuoteField(meta=missing, currency="USD"),
        kline=KlineField(meta=FieldMeta(status="missing", error="无")),
        technical=TechnicalField(meta=FieldMeta(status="missing", error="无")),
    )
    base.update(kw)
    return UnderlyingSnapshot(**base)


def test_currency_mismatch_rejected():
    with pytest.raises(ValidationError, match="币种"):
        _empty(currency="HKD")


def test_available_dividends_require_source_and_as_of():
    with pytest.raises(ValidationError, match="派息"):
        _empty(dividends=DividendField(meta=FieldMeta(status="available"), next_ex_date=D0))


def test_unavailable_vol_basis_cannot_carry_values():
    with pytest.raises(ValidationError, match="波动率基准"):
        _empty(vol_basis=VolBasisField(meta=FieldMeta(status="missing", error="无"), ratio=1.2))


def test_next_ex_date_before_snapshot_rejected():
    with pytest.raises(ValidationError, match="除息"):
        _empty(dividends=DividendField(
            meta=FieldMeta(status="available", source="futu_dividends", as_of=D0, fetched_at=NOW),
            next_ex_date=D0 - timedelta(days=1),
        ))


def _dividend_probe():
    return {
        **_fresh_probe(),
        "dividends": {
            "items": [
                {"ex_date": "2026-11-07", "record_date": "2026-11-09",
                 "payable_date": "2026-11-12", "pub_date": "2026-08-01",
                 "statement": "Cash Dividend: 0.27 USD Per Share"},
                {"ex_date": "2026-08-10", "record_date": None, "payable_date": None,
                 "pub_date": None, "statement": "Cash Dividend: 0.25 USD Per Share"},
            ],
            "history_count": 57,
            "error": None,
        },
        "vol_basis": {
            "iv_latest": 27.372, "hv_latest": 23.891, "iv_rank": 61.2, "hv_rank": 55.0,
            "ratio": 1.146, "as_of": "2026-09-22", "points": 250, "error": None,
        },
    }


def test_dividends_and_vol_basis_mapped_from_futu():
    snap = build_snapshot(
        ticker="US.AAPL", market="US", trade_date=D0, fetched_at=NOW, futu=_dividend_probe(),
    )
    assert snap.dividends.meta.status == "available"
    assert snap.dividends.next_ex_date == date(2026, 11, 7)
    assert len(snap.dividends.items) == 2
    assert snap.dividends.items[0].statement.startswith("Cash Dividend")
    assert snap.vol_basis.meta.status == "available"
    assert snap.vol_basis.ratio == 1.146
    assert snap.vol_basis.hv_rank == 55.0


def test_no_dividend_record_is_missing_not_available():
    probe = {**_fresh_probe(), "dividends": {"items": [], "history_count": 0, "error": None}}
    snap = build_snapshot(
        ticker="HK.03690", market="HK", trade_date=D0, fetched_at=NOW, futu=probe,
    )
    assert snap.dividends.meta.status == "missing"
    assert snap.dividends.next_ex_date is None
    assert "无派息" in (snap.dividends.meta.error or "")


def test_vol_basis_failure_is_missing_not_fabricated():
    probe = {**_fresh_probe(), "vol_basis": {"ratio": None, "error": "期权标的无此数据"}}
    snap = build_snapshot(
        ticker="US.AAPL", market="US", trade_date=D0, fetched_at=NOW, futu=probe,
    )
    assert snap.vol_basis.meta.status == "missing"
    assert snap.vol_basis.ratio is None


def test_coverage_entry_reports_new_fields():
    snap = build_snapshot(
        ticker="US.AAPL", market="US", trade_date=D0, fetched_at=NOW, futu=_dividend_probe(),
    )
    entry = coverage_entry(snap)
    assert entry["dividends"]["next_ex_date"] == "2026-11-07"
    assert entry["dividends"]["item_count"] == 2
    assert entry["vol_basis"]["has_ratio"] is True
    assert "27.372" not in json.dumps(entry)      # 脱敏账本不带数值


def test_available_quote_requires_last():
    with pytest.raises(ValidationError, match="last"):
        _empty(quote=QuoteField(
            meta=FieldMeta(status="available", source="futu", as_of=D0, fetched_at=NOW),
            currency="USD",
        ))


def test_fresh_snapshot_has_quote_kline_and_sma():
    snap = build_snapshot(
        ticker="US.AAPL", market="US", trade_date=D0, fetched_at=NOW,
        futu=_fresh_probe(),
    )
    assert snap.quote.meta.status == "available"
    assert snap.quote.last == 180.0
    assert snap.quote.currency == "USD"
    assert snap.kline.meta.status == "available"
    assert snap.kline.adjusted is True
    assert snap.kline.bars[-1].trade_date == D0
    assert snap.technical.meta.status == "available"
    assert "sma_5" in snap.technical.indicators
    assert snap.critical_gaps() == []
    assert snap.capital_flow.status == "unsupported"
    assert snap.fundamentals.status == "unsupported"
    assert snap.news.status == "unsupported"


def test_kline_must_end_on_the_session():
    snap = build_snapshot(
        ticker="US.AAPL", market="US", trade_date=D0, fetched_at=NOW,
        futu={
            "quote": {"last": 180, "session_date": D0.isoformat(), "error": None},
            "kline": {"adjusted": True, "bars": _bars(end=D0 - timedelta(days=1)), "error": None},
        },
    )
    assert snap.quote.meta.status == "available"
    assert snap.kline.meta.status == "stale"
    assert snap.kline.bars == []
    assert "这场交易" in (snap.kline.meta.error or "")


def test_preopen_monday_uses_friday_session():
    monday = date(2026, 9, 28)
    friday = date(2026, 9, 25)
    fetched = datetime(2026, 9, 28, 6, 12, tzinfo=timezone.utc)
    snap = build_snapshot(
        ticker="US.GLD", market="US", trade_date=monday, fetched_at=fetched,
        futu={
            "quote": {
                "last": 393.41,
                "session_date": monday.isoformat(),
                "update_time": "2026-09-28 02:12:35.650",
                "error": None,
            },
            "kline": {"adjusted": True, "bars": _bars(end=friday), "error": None},
        },
    )
    assert snap.as_of == friday
    assert snap.quote.meta.status == "available"
    assert snap.quote.last == 393.41
    assert snap.quote.meta.as_of == friday
    assert snap.kline.meta.status == "available"
    assert snap.kline.bars[-1].trade_date == friday
    assert snap.technical.meta.status == "available"
    assert "sma_5" in snap.technical.indicators


def test_closed_session_ignores_a_later_preopen_clock():
    wednesday = date(2026, 9, 23)
    fetched = datetime(2026, 9, 28, 6, 12, tzinfo=timezone.utc)
    snap = build_snapshot(
        ticker="US.AAPL", market="US", trade_date=wednesday, fetched_at=fetched,
        futu={
            "quote": {"last": 180.0, "session_date": wednesday.isoformat(), "error": None},
            "kline": {"adjusted": True, "bars": _bars(end=wednesday), "error": None},
        },
    )
    assert snap.as_of == wednesday
    assert snap.quote.meta.status == "available"
    assert snap.kline.meta.status == "available"
    assert snap.kline.meta.as_of == wednesday


def test_sunday_quote_uses_friday_session():
    sunday = date(2026, 9, 27)
    friday = date(2026, 9, 25)
    snap = build_snapshot(
        ticker="US.AAPL", market="US", trade_date=sunday, fetched_at=NOW,
        futu={
            "quote": {"last": 341.07, "session_date": friday.isoformat(), "error": None},
            "kline": {"adjusted": True, "bars": _bars(end=friday), "error": None},
        },
    )
    assert snap.as_of == friday
    assert snap.quote.meta.status == "available"
    assert snap.quote.last == 341.07
    assert snap.kline.meta.status == "available"
    assert snap.kline.meta.as_of == friday


def test_stale_quote_and_kline_drop_prices():
    old = (D0 - timedelta(days=10)).isoformat()
    snap = build_snapshot(
        ticker="US.AAPL", market="US", trade_date=D0, fetched_at=NOW,
        futu={
            "quote": {"last": 999, "session_date": old, "error": None},
            "kline": {"adjusted": True, "bars": _bars(end=D0 - timedelta(days=10)), "error": None},
        },
        fallback_error="降级源限流",
    )
    assert snap.quote.meta.status == "stale"
    assert snap.quote.last is None
    assert snap.kline.meta.status == "stale"
    assert snap.kline.bars == []
    assert snap.technical.indicators == {}
    assert snap.critical_gaps()


def test_fallback_records_futu_failure():
    snap = build_snapshot(
        ticker="HK.00700", market="HK", trade_date=D0, fetched_at=NOW,
        futu_error="opend 未连接",
        fallback=_fresh_probe(320.0),
        fallback_source="fmp",
    )
    assert snap.currency == "HKD"
    assert snap.quote.meta.status == "available"
    assert snap.quote.meta.source == "fmp"
    assert snap.quote.last == 320.0
    assert "opend 未连接" in (snap.quote.meta.error or "")
    assert snap.kline.meta.source == "fmp"


def test_both_sources_missing():
    snap = build_snapshot(
        ticker="US.AAPL", market="US", trade_date=D0, fetched_at=NOW,
        futu_error="opend 未连接",
        fallback_error="429",
    )
    assert snap.quote.meta.status == "missing"
    assert snap.quote.last is None
    assert "opend 未连接" in snap.quote.meta.error
    assert "429" in snap.quote.meta.error
    assert snap.kline.meta.status == "missing"


def test_short_kline_keeps_quote_but_technical_missing():
    snap = build_snapshot(
        ticker="US.AAPL", market="US", trade_date=D0, fetched_at=NOW,
        futu={
            "quote": {"last": 180, "session_date": D0.isoformat(), "error": None},
            "kline": {"adjusted": True, "bars": _bars(n=2), "error": None},
        },
    )
    assert snap.quote.meta.status == "available"
    assert snap.kline.meta.status == "available"
    assert snap.technical.meta.status == "missing"
    assert "SMA5" in (snap.technical.meta.error or "")
    assert snap.critical_gaps() == []


def test_coverage_ledger_omits_prices(tmp_path):
    snap = build_snapshot(
        ticker="US.AAPL", market="US", trade_date=D0, fetched_at=NOW,
        futu=_fresh_probe(188.5),
    )
    entry = coverage_entry(snap)
    blob = json.dumps(entry)
    assert "188.5" not in blob
    assert "sma_5" in entry["technical"]["indicator_names"]
    assert entry["capital_flow"]["status"] == "unsupported"
    path = write_coverage(D0, "US.AAPL", snap, runs_dir=tmp_path)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["tickers"]["US.AAPL"]["quote"]["status"] == "available"
    assert "last" not in saved["tickers"]["US.AAPL"]["quote"]
