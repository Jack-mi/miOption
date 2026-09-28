from datetime import date

import pytest

from signal_chain.config import NormTicker
from signal_chain.data import cboe


def _payload():
    return {"data": {
        "current_price": 149.5,
        "options": [
            {"option": "AAPL261016C00150000", "bid": 1.1, "ask": 1.2,
             "iv": 0.57, "delta": 0.2, "open_interest": 100.0, "volume": 3.0,
             "last_trade_price": 1.15},
            {"option": "AAPL261016P00140000", "bid": 0.8, "ask": 0.9,
             "iv": 0.56, "delta": -0.2, "open_interest": 200.0, "volume": 4.0,
             "last_trade_price": 0.85},
            {"option": "AAPL270101C00150000", "bid": 9.9, "ask": 10.0,
             "iv": 0.5, "delta": 0.3, "open_interest": 1.0, "volume": 0.0,
             "last_trade_price": 9.95},
        ],
    }}


def test_parse_chain_keeps_window_and_cboe_fields():
    chain = cboe.parse_chain(_payload(), NormTicker("US", "AAPL"), date(2026, 9, 23), 60)
    assert chain.source == "cboe"
    assert chain.degraded is True
    assert chain.spot == 149.5
    assert len(chain.rows) == 2
    call = chain.rows[0]
    assert call.code == "AAPL261016C00150000"
    assert call.strike == 150
    assert call.expiry == date(2026, 10, 16)
    assert call.iv == 0.57
    assert call.open_interest == 100


def test_parse_chain_rejects_empty_window():
    with pytest.raises(ValueError, match="窗口内无合约"):
        cboe.parse_chain(_payload(), NormTicker("US", "AAPL"), date(2026, 11, 1), 1)
