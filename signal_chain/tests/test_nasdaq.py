from datetime import date

from signal_chain.data import nasdaq


def test_daily_probe_parses_nasdaq_rows():
    payload = {"data": {"tradesTable": {"rows": [
        {"date": "09/23/2026", "close": "$100.00", "open": "$99.00",
         "high": "$101.00", "low": "$98.00", "volume": "1,234"},
        {"date": "09/22/2026", "close": "$99.00", "open": "$98.00",
         "high": "$100.00", "low": "$97.00", "volume": "999"},
    ]}}}
    probe = nasdaq.daily_probe(payload)
    assert probe is not None
    assert probe["quote"] == {
        "last": 100.0, "session_date": "2026-09-23", "error": None,
    }
    assert probe["kline"]["adjusted"] is False
    assert [b["trade_date"] for b in probe["kline"]["bars"]] == [
        "2026-09-22", "2026-09-23",
    ]
    assert probe["kline"]["bars"][-1]["volume"] == 1234


def test_daily_probe_rejects_empty_payload():
    assert nasdaq.daily_probe({"data": {"tradesTable": {"rows": []}}}) is None
