from __future__ import annotations

from datetime import date
from pathlib import Path

from mioption_runtime.futu.quote import OptionContract
from mioption_runtime.futu.trade import get_trade_backend
from mioption_runtime.seller.cards import WIKI_PATHS, card_id
from mioption_runtime.seller.follow import follow_once
from mioption_runtime.seller.monitor import MonitorParams, apply_verdict, mark_card, monitor_tick
from mioption_runtime.seller.payoff import conservative_credit, credit_vertical_payoff, settlement_pnl
from mioption_runtime.seller.scan import ScanParams, credit_vertical_candidates
from mioption_runtime.seller.store import SellerStore


def _put(code: str, strike: float, bid: float, ask: float, last: float, delta: float, expiry: str) -> OptionContract:
    return OptionContract(
        code=code,
        underlying="US.BIDU",
        strike=strike,
        expiry=expiry,
        option_type="PUT",
        bid=bid,
        ask=ask,
        last=last,
        delta=delta,
    )


class MapQuote:
    def __init__(self, spot: float, contracts: list[OptionContract], underlying: str = "US.BIDU"):
        self.spot = spot
        self.underlying = underlying
        self.chain = contracts
        self.by_code = {c.code: c for c in contracts}

    def snapshot(self, code: str) -> dict:
        if code == self.underlying:
            return {"code": code, "last_price": self.spot, "source": "map"}
        c = self.by_code[code]
        return {
            "code": code,
            "last_price": c.last,
            "bid_price": c.bid,
            "ask_price": c.ask,
            "option_delta": c.delta,
            "source": "map",
        }

    def option_chain(self, underlying: str, expiry: str | None = None) -> list[OptionContract]:
        return list(self.chain)


def _bidu_puts(expiry: str = "2026-09-11") -> list[OptionContract]:
    return [
        _put("US.BIDU260911P90000", 90.0, 0.01, 0.38, 0.09, -0.06, expiry),
        _put("US.BIDU260911P95000", 95.0, 0.64, 0.91, 0.70, -0.22, expiry),
        _put("US.BIDU260911P100000", 100.0, 1.92, 3.60, 2.59, -0.52, expiry),
    ]


BIDU_SCAN = ScanParams(dte_min=5, dte_max=21, min_credit=0.15, max_spread_vs_mid=5.0)


def test_bull_put_payoff_max_risk_and_breakeven():
    credit = conservative_credit(short_bid=0.64, long_ask=0.38)
    assert credit == 0.26
    pay = credit_vertical_payoff(
        "bull_put_spread",
        short_strike=95.0,
        long_strike=90.0,
        credit=credit,
    )
    assert pay["width"] == 5.0
    assert pay["max_profit"] == 26.0
    assert pay["max_loss"] == 474.0
    assert pay["breakeven"] == 94.74


def test_credit_vertical_candidates_bidu_put_spread():
    today = date(2026, 8, 30)
    cards = credit_vertical_candidates(
        "US.BIDU",
        99.47,
        _bidu_puts(),
        today=today,
        params=BIDU_SCAN,
    )
    assert cards
    card = next(c for c in cards if c.short.strike == 95.0 and c.long.strike == 90.0)
    assert card.structure_id == "bull_put_spread"
    assert card.wiki_path == WIKI_PATHS["bull_put_spread"]
    assert card.credit == 0.26
    assert card.max_loss == 474.0
    assert card.breakeven == 94.74
    assert "dte_12" in card.passed
    assert card.id == card_id("US.BIDU", "2026-09-11", "bull_put_spread", 95.0, 90.0)


def test_monitor_take_profit_does_not_place(tmp_path: Path):
    expiry = "2026-09-11"
    puts = _bidu_puts(expiry)
    # Cheap buyback: short ask 0.20, long bid 0.10 → debit 0.10 vs credit 0.26
    puts[1] = _put("US.BIDU260911P95000", 95.0, 0.10, 0.20, 0.15, -0.22, expiry)
    puts[0] = _put("US.BIDU260911P90000", 90.0, 0.10, 0.12, 0.11, -0.06, expiry)
    backend = MapQuote(99.47, puts)
    store = SellerStore(tmp_path)
    today = date(2026, 8, 30)
    card = credit_vertical_candidates(
        "US.BIDU",
        99.47,
        _bidu_puts(expiry),
        today=today,
        params=BIDU_SCAN,
    )[0]
    store.save_card(card)
    apply_verdict(store, card.id, "adopt")
    out = monitor_tick(
        store,
        backend,
        today=today,
        params=MonitorParams(take_profit_credit_frac=0.5),
    )
    kinds = [e["kind"] for e in out["events"]]
    assert "take_profit" in kinds
    assert out["place_order"] is False
    assert all(e.get("place_order") is False for e in out["events"] if e["kind"] == "take_profit")
    reloaded = store.get_card(card.id)
    assert reloaded is not None
    assert reloaded.status == "tracked"


def test_settlement_pnl_between_strikes():
    pnl = settlement_pnl(
        "bull_put_spread",
        short_strike=95.0,
        long_strike=90.0,
        credit=0.26,
        spot=93.0,
    )
    # intrinsic 2.00, credit 0.26 → -174
    assert pnl == -174.0


def test_follow_dry_run_places_nothing(tmp_path: Path):
    store = SellerStore(tmp_path)
    today = date(2026, 8, 30)
    card = credit_vertical_candidates(
        "US.BIDU",
        99.47,
        _bidu_puts(),
        today=today,
        params=BIDU_SCAN,
    )[0]
    store.save_card(card)
    apply_verdict(store, card.id, "adopt")
    trade = get_trade_backend(prefer_mock=True)
    before = list(getattr(trade, "_orders", {}))
    out = follow_once(store, trade=trade, submit=False, sequential=False, whitelist=["US.BIDU"])
    assert out["ok"] is True
    assert out["orders"][0]["placed"] is False
    assert out["orders"][0]["mode"] == "dry_run"
    after = list(getattr(trade, "_orders", {}))
    assert after == before
    saved = store.get_card(card.id)
    assert saved is not None
    assert saved.follow_status == "dry_run"


def test_mark_card_uses_quotes(tmp_path: Path):
    puts = _bidu_puts()
    card = credit_vertical_candidates(
        "US.BIDU",
        99.47,
        puts,
        today=date(2026, 8, 30),
        params=BIDU_SCAN,
    )[0]
    marked = mark_card(card, MapQuote(99.47, puts))
    assert marked.mark_close_debit is not None
    assert marked.mark_pnl is not None
