"""schema 校验：正例 + pydantic 负例。"""

from datetime import date

import pytest
from pydantic import ValidationError

from signal_chain.config import parse_ticker
from signal_chain.schema import (
    ChainSnapshot,
    Direction,
    EngineSignal,
    OptionRow,
)


def _signal(**kw):
    base = dict(
        signal_id="trend-US.AAPL-2026-09-23-deadbeef",
        engine="trend",
        raw_report_ref="/tmp/x.md",
        ticker="US.AAPL",
        market="US",
        as_of=date(2026, 9, 23),
        direction=Direction.BUY,
        conviction=0.5,
    )
    base.update(kw)
    return EngineSignal(**base)


def test_engine_signal_ok():
    s = _signal()
    assert s.direction == Direction.BUY
    assert s.horizon_days == (3, 20)
    assert s.volatility_view == "unknown"


def test_conviction_bounds():
    with pytest.raises(ValidationError):
        _signal(conviction=1.5)
    with pytest.raises(ValidationError):
        _signal(conviction=-1.01)


def test_market_literal():
    with pytest.raises(ValidationError):
        _signal(market="XX")


def test_ticker_parse():
    assert parse_ticker("AAPL").canonical == "US.AAPL"
    assert parse_ticker("0700.HK").canonical == "HK.00700"
    assert parse_ticker("hk00700").canonical == "HK.00700"
    assert parse_ticker("HK.700").canonical == "HK.00700"
    assert parse_ticker("600519").canonical == "CN.600519"
    assert parse_ticker("600519.SS").ta_format == "600519.SS"
    t = parse_ticker("HK.00700")
    assert (t.ta_format, t.futu_format) == ("0700.HK", "HK.00700")


def test_chain_atm_iv():
    rows = [
        OptionRow(code="C1", strike=100, expiry=date(2026, 10, 1),
                  option_type="CALL", iv=0.40),
        OptionRow(code="P1", strike=100, expiry=date(2026, 10, 1),
                  option_type="PUT", iv=0.42),
        OptionRow(code="C2", strike=100, expiry=date(2026, 11, 1),
                  option_type="CALL", iv=0.30),
    ]
    snap = ChainSnapshot(ticker="US.AAPL", market="US", as_of=date(2026, 9, 23),
                         source="futu", spot=100.0, rows=rows)
    assert snap.expiries() == [date(2026, 10, 1), date(2026, 11, 1)]
    front = snap.atm_iv(date(2026, 10, 1))
    assert front is not None and abs(front - 0.41) < 1e-6
