"""派息取数：per-symbol 记录优先，缺未来除息才扫派息日历兜底。不连 OpenD。"""

from datetime import date, timedelta

import pandas as pd

from signal_chain.options.underlying_bridge import _dividends

D0 = date(2026, 9, 30)          # 周三


class FakeQuoteCtx:
    def __init__(self, *, history=(), calendar=None, fail_days=()):
        self.history = list(history)
        self.calendar = calendar or {}
        self.fail_days = set(fail_days)
        self.scanned: list[str] = []

    def get_corporate_actions_dividends(self, symbol):
        return 0, {"dividend_list": self.history}

    def get_dividend_calendar(self, market, day):
        self.scanned.append(day)
        if day in self.fail_days:
            return -1, "high frequency"
        rows = self.calendar.get(day, [])
        return 0, (len(rows), pd.DataFrame(rows, columns=[
            "security", "name", "statement", "record_date", "ex_date",
            "dividend_payable_date"]))


def _row(ex_date, statement="Cash Dividend: 0.27 USD Per Share"):
    return {"ex_date": ex_date, "record_date": ex_date,
            "dividend_payable_date": ex_date, "pub_date": "07/31/2026",
            "statement": statement}


def test_future_entry_in_history_skips_the_calendar():
    ctx = FakeQuoteCtx(history=[_row("11/07/2026"), _row("08/10/2026")])
    out = _dividends(ctx, "US.AAPL", D0, 60, market=object())
    assert ctx.scanned == []                      # 有前瞻记录就别扫
    assert out["items"][0]["ex_date"] == "2026-11-07"
    assert out["history_count"] == 2


def test_calendar_fallback_finds_next_ex_date_on_a_weekday():
    hit_day = (D0 + timedelta(days=9)).isoformat()
    ctx = FakeQuoteCtx(
        history=[_row("08/10/2026")],
        calendar={hit_day: [{"security": "US.AAPL", "name": "Apple",
                             "statement": "Cash Dividend: 0.27 USD Per Share",
                             "record_date": hit_day, "ex_date": hit_day,
                             "dividend_payable_date": hit_day}]},
    )
    out = _dividends(ctx, "US.AAPL", D0, 60, market=object())
    assert out["items"][0]["ex_date"] == hit_day
    assert out["items"][1]["ex_date"] == "2026-08-10"     # 最近一次已发生还留着
    assert all(date.fromisoformat(d).weekday() < 5 for d in ctx.scanned)
    assert ctx.scanned[-1] <= hit_day


def test_first_hit_wins_even_if_a_later_day_has_the_same_symbol():
    day_a = (D0 + timedelta(days=2)).isoformat()      # 周五
    day_b = (D0 + timedelta(days=9)).isoformat()      # 下周五
    ctx = FakeQuoteCtx(history=[_row("08/10/2026")], calendar={
        day_a: [{"security": "US.AAPL", "ex_date": day_a, "statement": "A"}],
        day_b: [{"security": "US.AAPL", "ex_date": day_b, "statement": "B"}],
    })
    out = _dividends(ctx, "US.AAPL", D0, 60, market=object())
    assert out["items"][0]["ex_date"] == day_a


def test_stale_calendar_row_is_not_taken_as_upcoming():
    day = (D0 + timedelta(days=2)).isoformat()
    ctx = FakeQuoteCtx(
        history=[_row("08/10/2026")],
        calendar={day: [{"security": "US.AAPL", "ex_date": "09/01/2026", "statement": "A"}]},
    )
    out = _dividends(ctx, "US.AAPL", D0, 2, market=object())
    assert len(out["items"]) == 1                  # 只留下已发生那条，没被过去的日期顶上来
    assert out["items"][0]["ex_date"] == "2026-08-10"


def test_non_payer_does_not_scan():
    ctx = FakeQuoteCtx(history=[])
    out = _dividends(ctx, "HK.03690", D0, 60, market=object())
    assert ctx.scanned == []
    assert out["items"] == [] and out["history_count"] == 0


def test_scan_zero_and_missing_market_disable_the_fallback():
    ctx = FakeQuoteCtx(history=[_row("08/10/2026")])
    _dividends(ctx, "US.AAPL", D0, 0, market=object())
    _dividends(ctx, "US.AAPL", D0, 60, market=None)
    assert ctx.scanned == []


def test_single_failing_day_does_not_abort_the_scan():
    fail = (D0 + timedelta(days=1)).isoformat()
    hit_day = (D0 + timedelta(days=8)).isoformat()
    ctx = FakeQuoteCtx(
        history=[_row("08/10/2026")],
        calendar={hit_day: [{"security": "US.AAPL", "ex_date": hit_day, "statement": "A"}]},
        fail_days=[fail],
    )
    out = _dividends(ctx, "US.AAPL", D0, 60, market=object())
    assert fail in ctx.scanned
    assert out["items"][0]["ex_date"] == hit_day


def test_calendar_never_returns_another_symbol():
    day = (D0 + timedelta(days=4)).isoformat()
    ctx = FakeQuoteCtx(
        history=[_row("08/10/2026")],
        calendar={day: [{"security": "US.MSFT", "ex_date": day, "statement": "B"}]},
    )
    out = _dividends(ctx, "US.AAPL", D0, 5, market=object())
    assert out["items"][0]["ex_date"] == "2026-08-10"     # 只回落到已发生那条
    assert len(ctx.scanned) == 3                          # 5 天里跳过 2 天周末
