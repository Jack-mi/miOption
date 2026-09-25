"""标的快照契约：缺字段、过期、错币种、降级来源、脱敏账本。不访问 OpenD 或公网。"""

import json
from datetime import date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from signal_chain.options.underlying_fetch import build_snapshot, coverage_entry
from signal_chain.schema.underlying import (
    FieldMeta,
    KlineField,
    QuoteField,
    TechnicalField,
    UnderlyingSnapshot,
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


def test_previous_session_kline_stays_available():
    snap = build_snapshot(
        ticker="US.AAPL", market="US", trade_date=D0, fetched_at=NOW,
        futu={
            "quote": {"last": 180, "session_date": D0.isoformat(), "error": None},
            "kline": {"adjusted": True, "bars": _bars(end=D0 - timedelta(days=1)), "error": None},
        },
    )
    assert snap.quote.meta.status == "available"
    assert snap.kline.meta.status == "available"
    assert snap.kline.meta.as_of == D0 - timedelta(days=1)
    assert snap.kline.bars
    assert snap.technical.meta.status == "available"
    assert snap.critical_gaps() == []


def test_stale_quote_and_kline_drop_prices():
    old = (D0 - timedelta(days=10)).isoformat()
    snap = build_snapshot(
        ticker="US.AAPL", market="US", trade_date=D0, fetched_at=NOW,
        futu={
            "quote": {"last": 999, "session_date": old, "error": None},
            "kline": {"adjusted": True, "bars": _bars(end=D0 - timedelta(days=10)), "error": None},
        },
        yahoo_error="yfinance 限流",
    )
    assert snap.quote.meta.status == "stale"
    assert snap.quote.last is None
    assert snap.kline.meta.status == "stale"
    assert snap.kline.bars == []
    assert snap.technical.indicators == {}
    assert snap.critical_gaps()


def test_yahoo_fallback_records_futu_failure():
    snap = build_snapshot(
        ticker="HK.00700", market="HK", trade_date=D0, fetched_at=NOW,
        futu_error="opend 未连接",
        yahoo=_fresh_probe(320.0),
    )
    assert snap.currency == "HKD"
    assert snap.quote.meta.status == "available"
    assert snap.quote.meta.source == "yfinance"
    assert snap.quote.last == 320.0
    assert "opend 未连接" in (snap.quote.meta.error or "")
    assert snap.kline.meta.source == "yfinance"


def test_both_sources_missing():
    snap = build_snapshot(
        ticker="US.AAPL", market="US", trade_date=D0, fetched_at=NOW,
        futu_error="opend 未连接",
        yahoo_error="429",
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
