from __future__ import annotations

from pathlib import Path

from mioption_runtime.futu.quote_store import QuoteStore


def _pack(underlying: str, pulled_at: str, last: float, code_suffix: str) -> dict:
    return {
        "ok": True,
        "underlying": underlying,
        "pulled_at": pulled_at,
        "source": "futu",
        "days": 60,
        "windows": [{"start": "2026-09-07", "end": "2026-10-06"}],
        "coverage": {"chain_contracts": 2, "with_greeks": 2},
        "equity": {"code": underlying, "name": "Baidu", "last_price": last},
        "options": [
            {
                "code": f"{underlying}{code_suffix}C100000",
                "option_type": "CALL",
                "strike_time": "2026-09-11",
                "option_strike_price": 100.0,
                "bid_price": 2.1,
                "ask_price": 2.3,
                "last_price": 2.2,
                "option_delta": 0.5,
                "option_gamma": 0.06,
                "option_implied_volatility": 40.0,
                "option_open_interest": 12,
                "noise": "keep-in-extra",
            },
            {
                "code": f"{underlying}{code_suffix}P100000",
                "option_type": "PUT",
                "strike_time": "2026-09-11",
                "option_strike_price": 100.0,
                "bid_price": 1.1,
                "ask_price": 1.3,
                "last_price": 1.2,
                "option_delta": -0.5,
                "option_gamma": 0.06,
                "option_implied_volatility": 41.0,
            },
        ],
    }


def test_replace_current_keeps_three(tmp_path: Path):
    store = QuoteStore(tmp_path / "quotes.sqlite")
    for i in range(5):
        store.replace_current(_pack("US.BIDU", f"2026-09-0{i+1}T00:00:00Z", 90 + i, f"0{i}"))
    assert store.pull_count("US.BIDU") == 3
    cur = store.current("US.BIDU")
    assert cur is not None
    assert cur["equity"]["last_price"] == 94
    assert cur["count"] == 2
    assert cur["place_order"] is False
    assert cur["expiries"] == ["2026-09-11"]
    assert len(cur["chain"]) == 1
    assert cur["chain"][0]["strikes"][0]["call"]["delta"] == 0.5
    assert cur["chain"][0]["strikes"][0]["put"]["delta"] == -0.5
    call = next(c for c in cur["contracts"] if c["option_type"] == "CALL")
    assert call["delta"] == 0.5
    assert call["iv"] == 40.0
    detail = store.get_contract("US.BIDU", "US.BIDU04C100000")
    assert detail is not None
    assert detail["extra"].get("noise") == "keep-in-extra"


def test_other_underlying_untouched(tmp_path: Path):
    store = QuoteStore(tmp_path / "quotes.sqlite")
    store.replace_current(_pack("US.BIDU", "t1", 99, "A"))
    store.replace_current(_pack("US.TSLA", "t2", 250, "B"))
    assert store.current("US.BIDU")["equity"]["last_price"] == 99
    assert store.current("US.TSLA")["equity"]["last_price"] == 250
