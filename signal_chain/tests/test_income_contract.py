"""Generic read-only income contract shared with the seller desk."""

from datetime import date, datetime, timedelta, timezone

from mioption_runtime.futu.quote import MockQuoteBackend
from mioption_runtime.futu.quote_store import QuoteStore
from mioption_runtime.seller.income import candidates, drawdown_warning, evaluate
from mioption_runtime.seller.scan import scan_watchlist
from signal_chain.options.strategy_menu import screen_menu
from signal_chain.schema import ChainSnapshot, Direction, EnsembleSignal, OptionRow

DAY = date(2026, 9, 28)
NOW = datetime(2026, 9, 28, 14, 5, tzinfo=timezone.utc)
STAMP = "2026-09-28 10:04:45"
EXPIRY = date(2026, 10, 9)


def closes(last=100.0):
    days = [DAY - timedelta(days=n) for n in (10, 7, 6, 5, 4, 3)]
    return [(day, last) for day in days]


def account(now=NOW):
    return {"env": "REAL", "currency": "USD", "value": 100_000,
            "available_cash_usd": 1000, "positions": [], "fetched_at": now.isoformat()}


def legs(short_bid=1.5, long_ask=.5):
    return (
        {"code": "P95", "option_type": "PUT", "expiry": EXPIRY, "strike": 95.0,
         "bid": short_bid, "ask": short_bid + .1, "open_interest": 250,
         "quoted_at": STAMP, "fetched_at": NOW.isoformat(), "contract_size": 100},
        {"code": "P90", "option_type": "PUT", "expiry": EXPIRY, "strike": 90.0,
         "bid": long_ask - .04, "ask": long_ask, "open_interest": 250,
         "quoted_at": STAMP, "fetched_at": NOW.isoformat(), "contract_size": 100},
    )


def grade(short=None, long=None, **overrides):
    short, long = (short, long) if short is not None else legs()
    data = dict(spot=100.0, spot_at=STAMP, source="futu", now=NOW,
                account=account(), closes=closes(), earnings=date(2026, 11, 20),
                signal_ok=True, review_ok=True, fetched_at=NOW.isoformat(),
                spot_fetched_at=NOW.isoformat())
    data.update(overrides)
    return evaluate(short, long, **data)


def test_two_entrypoints_share_price_and_tier():
    short, long = legs()
    direct = grade(short, long)
    chain = ChainSnapshot(ticker="US.TEST", market="US", as_of=DAY, source="futu",
                          spot=100, spot_at=STAMP, spot_fetched_at=NOW.isoformat(), fetched_at=NOW,
                          rows=[OptionRow(**row) for row in (short, long)])
    signal = EnsembleSignal(ticker="US.TEST", market="US", as_of=DAY, components=[],
                            agreement="aligned", direction=Direction.BUY, conviction=.6)
    menu = screen_menu(signal, chain, now=NOW, today=DAY, account=account(),
                       closes=closes(), earnings_date=date(2026, 11, 20))
    candidate = next(v for v in menu if v.income)
    assert direct["tier"] == candidate.tier == "可考虑"
    assert direct["credit"] == candidate.proposal.net_premium == 100
    assert direct["max_loss"] == candidate.proposal.max_loss == 400


def test_midpoint_premium_cannot_override_conservative_bid_ask():
    short, long = legs(.75, .5)
    result = grade(short, long)
    assert result["credit"] == 25
    assert result["max_loss"] == 475
    assert result["tier"] == "仅观察"
    assert any("收益" in reason for reason in result["reasons"])


def test_missing_age_and_partial_chain_never_upgrade():
    short, long = legs()
    for change in ({"spot_at": None}, {"complete": False}, {"source": "cboe"},
                   {"account": None}, {"review_ok": False}, {"signal_ok": False},
                   {"earnings": None}):
        assert grade(short, long, **change)["tier"] == "仅观察"
    assert grade(short, long, now=NOW + timedelta(minutes=2))["tier"] == "仅观察"
    assert grade(short, long, earnings=date(2026, 10, 6))["tier"] == "仅观察"
    assert grade(short, long, account=account(NOW - timedelta(minutes=6)))["tier"] == "仅观察"


def test_invalid_structure_and_unknown_multiplier_are_forbidden():
    short, long = legs()
    assert grade(short, {**long, "contract_size": None})["tier"] == "仅观察"
    assert grade(short, {**long, "contract_size": 10})["tier"] == "禁做"
    assert grade(short, {**long, "ask": 2.0})["tier"] == "禁做"
    assert grade(short, {**long, "expiry": date(2026, 10, 16)})["tier"] == "禁做"


def test_completed_sessions_drawdown_and_recovery():
    days = [date(2026, 9, day) for day in (10, 11, 14, 15, 16, 17, 18, 21, 22, 23, 24, 25)]
    prices = [100, 100, 100, 100, 100, 100, 89, 90, 91, 92, 93, 94]
    series = list(zip(days, prices))
    assert drawdown_warning(series[:7], datetime(2026, 9, 18, 21, tzinfo=timezone.utc), .10)
    assert not drawdown_warning(series, NOW, .10)
    assert grade(closes=series)["tier"] == "可考虑"
    assert grade(closes=series[:-1])["tier"] == "仅观察"
    assert drawdown_warning([(day, (88 if day == date(2026, 9, 24) else price))
                             for day, price in series], NOW, .10)


def test_offhours_is_conditional_only_with_verified_close():
    short, long = legs()
    previous = "2026-09-25 15:58:00"
    sunday = datetime(2026, 9, 27, 18, tzinfo=timezone.utc)
    historical = [(date(2026, 9, day), 100) for day in (17, 18, 21, 22, 23, 24, 25)]
    result = grade({**short, "quoted_at": previous, "fetched_at": sunday.isoformat()},
                   {**long, "quoted_at": previous, "fetched_at": sunday.isoformat()},
                   spot_at=previous, now=sunday, account=account(sunday), closes=historical,
                   fetched_at=sunday.isoformat(), spot_fetched_at=sunday.isoformat())
    assert result["tier"] == "条件可考虑，开盘须重报价"
    assert grade({**short, "quoted_at": previous}, {**long, "quoted_at": previous},
                 spot_at=previous, now=NOW)["tier"] == "仅观察"


def test_candidate_enumeration_not_at_the_money_only():
    rows = [dict(row) for row in legs()]
    assert candidates(rows, 100, NOW) == [tuple(rows)]
    assert candidates([*rows, {**rows[0], "strike": None}], 100, NOW) == [tuple(rows)]


def test_earnings_window_uses_evaluation_date_not_expiry():
    assert grade(earnings=date(2026, 10, 6))["tier"] == "仅观察"
    assert grade(earnings=date(2026, 10, 20))["tier"] == "可考虑"


def test_missing_fetch_or_wrong_currency_cannot_upgrade():
    assert grade(fetched_at=None)["tier"] == "仅观察"
    assert grade(spot_fetched_at=None)["tier"] == "仅观察"
    assert grade(fetched_at=(NOW - timedelta(minutes=2)).isoformat())["tier"] == "仅观察"
    assert grade(account={**account(), "currency": "HKD"})["tier"] == "仅观察"
    assert grade(account={**account(), "value": float("nan")})["tier"] == "仅观察"
    assert grade(account={**account(), "available_cash_usd": None})["tier"] == "仅观察"
    assert grade(account={**account(), "positions": None})["tier"] == "仅观察"


def test_seller_scan_matches_menu_from_same_persisted_evidence(tmp_path):
    short, long = legs()
    chain = ChainSnapshot(ticker="US.TEST", market="US", as_of=DAY, source="futu", spot=100,
                          spot_at=STAMP, spot_fetched_at=NOW.isoformat(), fetched_at=NOW,
                          rows=[OptionRow(**row) for row in (short, long)])
    signal = EnsembleSignal(ticker="US.TEST", market="US", as_of=DAY, components=[],
                            agreement="aligned", direction=Direction.BUY, conviction=.6)
    menu = next(item for item in screen_menu(signal, chain, now=NOW, today=DAY, account=account(),
                     closes=closes(), earnings_date=date(2026, 11, 20)) if item.income)
    pack = {"underlying": "US.TEST", "source": "futu", "pulled_at": NOW.isoformat(),
            "days": 60, "equity": {"last_price": 100, "update_time": STAMP,
                                    "fetched_at": NOW.isoformat()},
            "coverage": {"chain_contracts": 2, "option_snapshots": 2},
            "options": [{**row, "strike_time": EXPIRY.isoformat(),
                         "option_strike_price": row["strike"], "bid_price": row["bid"],
                         "ask_price": row["ask"], "option_open_interest": 250,
                         "option_contract_size": 100, "update_time": STAMP} for row in (short, long)]}
    quotes = QuoteStore(tmp_path / "quotes.sqlite")
    quotes.replace_current(pack)
    scanned = scan_watchlist(MockQuoteBackend(), underlyings=["US.TEST"], quote_store=quotes,
                             now=NOW, evidence={"US.TEST": {"account": account(), "closes": closes(),
                             "earnings": date(2026, 11, 20), "signal_ok": True,
                             "signal_direction": "buy", "review_ok": True}})
    card = next(card for card in scanned["cards"] if card["short"]["code"] == short["code"])
    assert (scanned["errors"], card["tier"], card["max_loss"], card["max_profit"]) == (
        {}, menu.tier, menu.proposal.max_loss, menu.proposal.max_profit)


def test_anonymized_open_d_bid_ask_regression():
    short, long = legs()
    short.update(bid=.54, ask=.73)
    long.update(bid=.33, ask=.44)
    midpoint = ((short["bid"] + short["ask"]) - (long["bid"] + long["ask"])) / 2
    assert midpoint / (2.5 - midpoint) >= .10
    result = grade(short, {**long, "strike": 92.5}, spot=100)
    assert result["tier"] == "仅观察"
    assert result["return_on_risk"] < .10


def test_shortened_session_and_holiday_close():
    from mioption_runtime.seller.income import _session_time

    close = "2026-11-27 12:58:00"
    now = datetime(2026, 11, 27, 19, tzinfo=timezone.utc)
    tier, reasons = _session_time(close, close, close, now, "futu", {"quote_max_age_seconds": 60})
    assert (tier, reasons) == ("条件可考虑，开盘须重报价", [])
    stale = "2026-11-27 15:58:00"
    assert _session_time(stale, stale, stale, now, "futu", {"quote_max_age_seconds": 60})[0] == "仅观察"
    assert _session_time(close, close, close, now + timedelta(days=4), "futu",
                         {"quote_max_age_seconds": 60})[0] == "仅观察"


def test_partial_persisted_chain_and_missing_decision_stay_observation(tmp_path):
    short, long = legs()
    pack = {"underlying": "US.TEST", "source": "futu", "pulled_at": NOW.isoformat(),
            "equity": {"last_price": 100, "update_time": STAMP, "fetched_at": NOW.isoformat()},
            "coverage": {"chain_contracts": 2, "option_snapshots": 1},
            "options": [{**row, "option_strike_price": row["strike"],
                         "option_open_interest": 250, "option_contract_size": 100,
                         "update_time": STAMP} for row in (short, long)]}
    store = QuoteStore(tmp_path / "quotes.sqlite")
    store.replace_current(pack)
    evidence = {"US.TEST": {"account": account(), "closes": closes(),
                            "earnings": date(2026, 11, 20), "signal_ok": True,
                            "signal_direction": "buy", "review_ok": True}}
    result = scan_watchlist(MockQuoteBackend(), underlyings=["US.TEST"],
                            quote_store=store, evidence=evidence, now=NOW)
    assert result["cards"]
    assert all(card["tier"] == "仅观察" for card in result["cards"])
    assert any("期权链未完整" in reason for reason in result["cards"][0]["tier_reasons"])
    missing = scan_watchlist(MockQuoteBackend(), underlyings=["US.TEST"], quote_store=store, now=NOW)
    assert all(card["tier"] == "仅观察" for card in missing["cards"])
    assert scan_watchlist(MockQuoteBackend(), underlyings=["HK.TEST"], now=NOW)["errors"]
