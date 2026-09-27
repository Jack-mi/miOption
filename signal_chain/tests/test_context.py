"""上下文切片。用假快照，不访问公网。"""

from datetime import date, datetime, timezone

from signal_chain.data.context import card, slice
from signal_chain.data.models import EventOdds, Fact, FilingExcerpt, MacroPoint, MarketData, SourceRow
from signal_chain.options.underlying_fetch import build_snapshot
from signal_chain.schema.underlying import FieldMeta
from signal_chain.schema.options import ChainSnapshot, OptionRow

D0 = date(2026, 9, 23)
NOW = datetime(2026, 9, 23, 20, 0, tzinfo=timezone.utc)


def _market():
    snap = build_snapshot(
        ticker="US.AAPL", market="US", trade_date=D0, fetched_at=NOW,
        futu={
            "quote": {"last": 180.0, "session_date": D0.isoformat(), "error": None},
            "kline": {"adjusted": True, "bars": [{
                "trade_date": D0.isoformat(),
                "open": 1, "high": 2, "low": 1, "close": 1, "volume": 1,
            }], "error": None},
        },
    ).model_copy(update={"fundamentals": FieldMeta(
        status="available", source="edgar", as_of=D0, fetched_at=NOW, period="Q2026-06-27",
    )})
    chain = ChainSnapshot(
        ticker="US.AAPL", market="US", as_of=D0, source="futu", spot=180.0,
        rows=[
            OptionRow(code="C1", strike=180, expiry=date(2026, 10, 16), option_type="CALL"),
            OptionRow(code="C2", strike=185, expiry=date(2026, 11, 20), option_type="CALL"),
        ],
    )
    return MarketData(
        snapshot=snap,
        chain=chain,
        facts=[Fact("edgar", "revenue", "Q2026-06-27", 109.0)],
        sources=[
            SourceRow("edgar", "earnings", "used", "申报日 2026-07-31"),
            SourceRow("nasdaq", "earnings", "used", "Nasdaq 2026-10-29；Finnhub EPS预期 2.02"),
        ],
        excerpts=[
            FilingExcerpt("risk_factors", "供应链中断", "edgar", D0, "summary full=68037"),
        ],
        events=[EventOdds("aapl-up", "yes", 0.4)],
        macro=[MacroPoint("CPI", date(2026, 8, 1), 334.0)],
    )


def test_card_names_the_four_clocks():
    text = card(_market())
    assert "US.AAPL" in text
    assert "2026-09-23" in text
    assert "盘面" in text and "财报" in text and "消息" in text and "宏观" in text


def test_each_slice_is_nonempty_when_present_or_missing():
    market = _market()
    bare = build_snapshot(ticker="US.AAPL", market="US", trade_date=D0, fetched_at=NOW)
    empty = MarketData(snapshot=bare)
    for name in (
        "quote", "kline", "sma", "flow", "chain",
        "fundamentals", "earnings", "filing",
        "business", "competition", "risk", "governance",
        "news", "social", "events", "macro",
    ):
        assert slice(market, name)
        assert slice(empty, name)


def test_research_slices_show_filing_and_chain_summary():
    market = _market()
    assert "申报日 2026-07-31" in slice(market, "filing")
    chain = slice(market, "chain")
    assert "2 张" in chain and "2 个到期" in chain and "180" in chain
    assert "C1" not in chain


def test_value_slices_show_quarter_revenue_and_risk_summary():
    market = _market()
    assert "109.0" in slice(market, "fundamentals")
    assert "Q2026-06-27" in slice(market, "fundamentals")
    risk = slice(market, "risk")
    assert "供应链中断" in risk and "full=68037" in risk
