"""数据层字段并行，价格仍按级联。注入假响应，不访问 OpenD 或公网。"""

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from signal_chain.config import NormTicker
from signal_chain.data import earnings_calendar, edgar, fmp, polymarket
from signal_chain.data.layer import _price_rows, clear_macro_cache, load
from signal_chain.options.underlying_fetch import build_snapshot
from signal_chain.schema.underlying import UnderlyingSnapshot

D0 = date(2026, 9, 23)
NOW = datetime(2026, 9, 23, 20, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _quiet():
    clear_macro_cache()


def _bars():
    rows = []
    for i in range(5):
        day = date.fromordinal(D0.toordinal() - 4 + i)
        px = 100 + i
        rows.append({
            "trade_date": day.isoformat(),
            "open": px, "high": px + 1, "low": px - 1, "close": px, "volume": 10,
        })
    return rows


def _futu(price=180.0, flow=True):
    payload = {
        "quote": {"last": price, "session_date": D0.isoformat(), "error": None},
        "kline": {"adjusted": True, "bars": _bars(), "error": None},
    }
    if flow:
        payload["capital_flow"] = {"net": 12.0, "as_of": D0.isoformat(), "error": None}
    return payload


def test_stale_kline_is_not_recorded_as_a_successful_fetch():
    snap = build_snapshot(
        ticker="US.AAPL", market="US", trade_date=D0, fetched_at=NOW,
        futu={
            "quote": {"last": 180.0, "session_date": D0.isoformat(), "error": None},
            "kline": {"adjusted": True, "bars": _bars()[:-1], "error": None},
        },
    )
    row = next(item for item in _price_rows(snap, {"futu": "ok"}) if item.field == "kline")
    assert row.id == "futu"
    assert row.state == "stale"
    assert "不是这场交易" in row.note


def _states(market, field):
    return {(row.id, row.state) for row in market.sources if row.field == field}


def _load(*, market="US", code="AAPL", futu=None, futu_error=None,
          keys=None, get=None, quota=None, get_text=None, settings=None,
          include_chain=False, chain_fetch=None):
    ticker = NormTicker(market, code)

    def futu_probe(*_a, **_k):
        return futu, futu_error

    def getter(url, headers=None):
        if get:
            return get(url, headers)
        raise AssertionError(url)

    return load(
        ticker, D0, settings or object(), include_chain=include_chain,
        keys=keys or {},
        get=getter,
        quota=quota or (lambda: False),
        futu_probe=futu_probe,
        chain_fetch=chain_fetch or (lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("不该取链"))),
        fetch_macro=lambda: [],
        **({} if get_text is None else {"get_text": get_text}),
    )


def _edgar_get(url, headers=None):
    if "company_tickers" in url:
        return {"0": {"ticker": "AAPL", "cik_str": 320193}}
    if "companyfacts" in url:
        return {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
            {"form": "10-K", "val": 100.0, "end": "2025-09-27"},
        ]}}}}}
    if "submissions" in url:
        return {"filings": {"recent": {"form": ["10-Q"], "filingDate": ["2026-08-01"]}}}
    if "stocktwits" in url:
        return {"messages": []}
    raise AssertionError(url)


def test_fresh_futu_skips_fmp_price():
    market = _load(futu=_futu(), get=_edgar_get)
    assert market.snapshot.quote.meta.source == "futu"
    assert market.snapshot.kline.meta.source == "futu"
    assert ("fmp", "skipped") in _states(market, "quote")
    assert ("futu", "used") in _states(market, "capital_flow")
    assert ("eastmoney", "skipped") not in _states(market, "capital_flow")
    assert market.snapshot.fundamentals.status == "available"
    assert market.snapshot.fundamentals.source == "edgar"
    assert market.facts and market.facts[0].source == "edgar"
    assert market.snapshot.earnings_date is None
    assert market.snapshot.earnings_source is None
    assert any(row.id == "edgar" and row.state == "used" and "申报日 2026-08-01" in row.note
               for row in market.sources if row.field == "earnings")
    assert ("supabase", "missing") in _states(market, "macro")
    assert ("polymarket", "skipped") in _states(market, "events")


def test_fmp_fills_quote_when_futu_misses():
    def get(url, headers=None):
        if "historical-price-eod" in url:
            return [{"date": D0.isoformat(), "open": 90, "high": 91, "low": 89, "close": 90, "volume": 1}]
        if "stocktwits" in url:
            return {"messages": [{"body": "看多"}]}
        if "sec.gov" in url:
            raise RuntimeError("edgar 暂停")
        raise AssertionError(url)

    market = _load(
        futu=None, futu_error="opend 未连接",
        keys={"FMP_API_KEY": "k"}, get=get, quota=lambda: True,
    )
    assert market.snapshot.quote.meta.source == "fmp"
    assert market.snapshot.quote.last == 90
    assert "opend 未连接" in (market.snapshot.quote.meta.error or "")
    assert ("reddit", "missing") in _states(market, "social")


def test_nasdaq_fills_price_when_futu_and_fmp_miss():
    def get(url, headers=None):
        if "api.nasdaq.com/api/quote/AAPL/historical" in url:
            return {"data": {"tradesTable": {"rows": [
                {"date": "09/23/2026", "close": "$91.00", "open": "$90.00",
                 "high": "$92.00", "low": "$89.00", "volume": "100"},
            ]}}}
        if "sec.gov" in url:
            return _edgar_get(url, headers)
        raise AssertionError(url)

    market = _load(futu=None, futu_error="opend 未连接", get=get)
    assert market.snapshot.quote.meta.source == "nasdaq"
    assert market.snapshot.quote.last == 91.0
    assert market.snapshot.kline.meta.source == "nasdaq"
    assert ("fmp", "skipped") in _states(market, "quote")
    assert ("nasdaq", "used") in _states(market, "quote")


def test_chain_spot_uses_the_price_cascade_spot():
    from signal_chain.schema import ChainSnapshot, OptionRow

    exp = D0 + timedelta(days=14)
    futu_chain = ChainSnapshot(
        ticker="US.AAPL", market="US", as_of=D0, source="futu", spot=101.0,
        rows=[OptionRow(code="C100", strike=100, expiry=exp, option_type="CALL",
                        bid=5, ask=5.2, open_interest=500)],
    )
    market = _load(
        futu=_futu(100.0), get=_edgar_get, include_chain=True,
        chain_fetch=lambda *_a, **_k: futu_chain,
    )
    assert market.chain is not None
    assert market.chain.source == "futu"
    assert market.chain.spot == 100.0
    assert ("cboe", "skipped") in _states(market, "chain")


def test_cboe_fills_chain_when_futu_fails():
    def get(url, headers=None):
        if "cdn-api.cboe.com/api/global/delayed_quotes/options/AAPL.json" in url:
            return {
                "data": {
                    "current_price": 101.0,
                    "options": [{
                        "option": "AAPL261007C00100000", "bid": 1.0, "ask": 1.1,
                        "iv": 0.3, "delta": 0.5, "open_interest": 100.0,
                        "volume": 1.0, "last_trade_price": 1.05,
                    }],
                },
            }
        if "sec.gov" in url:
            return _edgar_get(url, headers)
        raise AssertionError(url)

    def chain_fetch(*_a, **_k):
        raise RuntimeError("OpenD 未连接")

    market = _load(
        futu=_futu(100.0), get=get, include_chain=True, chain_fetch=chain_fetch,
        settings=SimpleNamespace(chain={"expiry_window_days": 60}),
    )
    assert market.chain is not None
    assert market.chain.source == "cboe"
    assert market.chain.degraded is True
    assert market.chain.spot == 100.0
    assert ("futu", "missing") in _states(market, "chain")
    assert ("cboe", "used") in _states(market, "chain")


def test_fmp_price_when_both_fail():
    def get(url, headers=None):
        if "historical-price-eod" in url:
            return [
                {"date": "2026-09-19", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 1},
                {"date": D0.isoformat(), "open": 10, "high": 12, "low": 9, "close": 11, "volume": 2},
            ]
        if "income-statement?symbol" in url:
            return [{"revenue": 100, "date": "2025-09-27"}]
        if "company-news" in url:
            return [{"headline": "Finnhub 新闻"}]
        if "company_tickers" in url:
            return {"0": {"ticker": "AAPL", "cik_str": 320193}}
        if "companyfacts" in url:
            return {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
                {"form": "10-K", "val": 100.0, "end": "2025-09-27"},
            ]}}}}}
        if "submissions" in url:
            return {"filings": {"recent": {"form": ["10-K"], "filingDate": ["2026-01-30"]}}}
        if "stocktwits" in url:
            return {"messages": [{"body": "也在说"}]}
        raise AssertionError(url)

    market = _load(
        futu=None, futu_error="opend 未连接",
        keys={"FMP_API_KEY": "k", "FINNHUB_API_KEY": "h"}, get=get, quota=lambda: True,
    )
    assert market.snapshot.quote.meta.source == "fmp"
    assert market.snapshot.quote.last == 11.0
    assert market.snapshot.news.source == "finnhub"
    assert market.news_text == "Finnhub 新闻"
    assert market.snapshot.fundamentals.status == "available"
    assert market.social == []


def test_non_us_load_does_not_fetch():
    def refuse(*_a, **_k):
        raise AssertionError("不该取数")

    result = load(
        NormTicker("HK", "00700"), D0, object(), include_chain=False,
        keys={"FMP_API_KEY": "k"},
        get=refuse, quota=lambda: True,
        futu_probe=refuse, chain_fetch=refuse,
    )
    assert result.chain_error == "只覆盖美股"
    assert ("loader", "unsupported") in _states(result, "market")
    with pytest.raises(ValueError, match="只覆盖美股"):
        load(
            NormTicker("CN", "600519"), D0, object(), include_chain=False,
            get=refuse, futu_probe=refuse, chain_fetch=refuse,
        )


def test_capital_flow_available_requires_source():
    snap = build_snapshot(
        ticker="US.AAPL", market="US", trade_date=D0, fetched_at=NOW, futu=_futu(),
    )
    data = snap.model_dump()
    data["capital_flow"] = {"status": "available"}
    with pytest.raises(ValidationError, match="资金流"):
        UnderlyingSnapshot.model_validate(data)
    data["capital_flow"] = {
        "status": "available", "source": "futu",
        "as_of": D0.isoformat(), "fetched_at": NOW.isoformat(),
    }
    ok = UnderlyingSnapshot.model_validate(data)
    assert ok.capital_flow.status == "available"


def test_macro_reads_latest_fred_observation():
    def get(url, headers=None):
        if "/rest/v1/macro_latest" in url:
            assert headers and headers.get("apikey")
            return [
                {"series": "FEDERAL_FUNDS_RATE", "as_of": "2026-09-24", "value": 4.09,
                 "source": "fred", "fetched_at": "2026-09-28T00:00:00Z"},
                {"series": "RISK_FREE_3M", "as_of": "2026-09-24", "value": 3.95,
                 "source": "fred", "fetched_at": "2026-09-28T00:00:00Z"},
                {"series": "CPI", "as_of": "2026-08-01", "value": 326.8,
                 "source": "fred", "fetched_at": "2026-09-28T00:00:00Z"},
                {"series": "UNEMPLOYMENT", "as_of": "2026-08-01", "value": 4.3,
                 "source": "fred", "fetched_at": "2026-09-28T00:00:00Z"},
                {"series": "DGS10", "as_of": "2026-09-24", "value": 4.16,
                 "source": "fred", "fetched_at": "2026-09-28T00:00:00Z"},
            ]
        if "sec.gov" in url or "stocktwits" in url:
            return _edgar_get(url, headers)
        raise AssertionError(url)

    market = _load(futu=_futu(), keys={"SUPABASE_SERVICE_ROLE_KEY": "k"}, get=get)
    by_series = {point.series: point for point in market.macro}
    assert by_series["FEDERAL_FUNDS_RATE"].as_of == date(2026, 9, 24)
    assert by_series["FEDERAL_FUNDS_RATE"].value == 4.09
    assert by_series["FEDERAL_FUNDS_RATE"].source == "fred"
    assert by_series["CPI"].value == 326.8
    assert by_series["UNEMPLOYMENT"].value == 4.3
    assert by_series["DGS10"].as_of == date(2026, 9, 24)
    assert by_series["DGS10"].value == 4.16
    assert by_series["RISK_FREE_3M"].value == 3.95
    assert ("supabase", "used") in _states(market, "macro")
    assert ("fmp", "used") not in _states(market, "macro")
    assert ("fred", "used") not in _states(market, "macro")
    from signal_chain.decision.pack import render_pack
    text = render_pack(market)
    assert "FEDERAL_FUNDS_RATE" in text
    assert "4.09" in text


def test_macro_shared_layer_missing_without_supabase_key():
    market = _load(futu=_futu(), get=_edgar_get)
    assert market.macro == []
    assert ("supabase", "missing") in _states(market, "macro")


def test_earnings_date_stays_empty_without_a_disclosure_source():
    market = _load(futu=_futu(), get=_edgar_get)
    assert market.snapshot.earnings_date is None
    assert market.snapshot.earnings_source is None
    assert any("申报日 2026-08-01" in row.note for row in market.sources if row.field == "earnings")


def test_agreed_ratios_excerpts_and_fresh_archive():
    from signal_chain.decision.pack import render_pack

    def gaap(name, val):
        return {name: {"units": {"USD": [{"form": "10-K", "val": val, "end": "2025-09-27"}]}}}

    def get(url, headers=None):
        if "company_tickers" in url:
            return {"0": {"ticker": "AAPL", "cik_str": 320193}}
        if "companyfacts" in url:
            merged = {}
            for name, val in (
                ("Revenues", 100), ("NetIncomeLoss", 10), ("StockholdersEquity", 100),
                ("NetCashProvidedByUsedInOperatingActivities", 30),
                ("PaymentsToAcquirePropertyPlantAndEquipment", 10),
                ("OperatingIncomeLoss", 8), ("InterestExpense", 2),
            ):
                merged.update(gaap(name, val))
            return {"facts": {"us-gaap": merged}}
        if "submissions" in url:
            return {"filings": {"recent": {
                "form": ["10-K", "DEF 14A"],
                "filingDate": ["2026-01-30", "2026-02-01"],
                "accessionNumber": ["0000320193-26-000001", "0000320193-26-000002"],
                "primaryDocument": ["a10k.htm", "proxy.htm"],
            }}}
        raise AssertionError(url)

    def read_text(url, headers=None):
        if url.endswith("a10k.htm"):
            return (
                "Item 1. Business The company sells devices and services to a global installed base. "
                "Item 1A. Risk Factors Supply concentration can interrupt production for months. "
                "Item 1B. Unresolved Staff Comments None here."
            )
        return (
            "Corporate Governance The board reviews capital allocation with the audit committee each quarter. "
            "Executive Compensation See the following table."
        )

    market = _load(
        futu=_futu(), get=get, get_text=read_text,
    )
    assert market.ratios == []
    assert any(fact.source == "edgar" and fact.metric == "roe" for fact in market.facts)
    assert {item.section for item in market.excerpts} == {"business", "risk_factors", "governance"}
    assert ("reddit", "missing") in _states(market, "social")
    from signal_chain.research.workflow import role_gap_labels, role_memo
    assert "sells devices" in role_memo(market)
    assert "商业模式缺失" not in role_gap_labels(market)
    assert "竞争缺失" in role_gap_labels(market)
    text = render_pack(market)
    assert "商业模式" in text and "sells devices" in text
    assert "竞争缺失" in text
    assert "risk_factors" in text
    assert "宏观缺失" in text


def test_social_stays_missing_without_reddit_credentials():
    market = _load(futu=_futu(), get=_edgar_get)
    assert market.social == []
    assert ("reddit", "missing") in _states(market, "social")
    assert all(row.id != "stocktwits" for row in market.sources)


def test_macro_odds_keep_the_group_and_drop_thin_markets():
    events = [
        {"title": "Fed cuts", "slug": "fed-cuts", "markets": [
            {"question": "No cuts", "closed": False, "negRisk": True,
             "outcomePrices": "[\"0.9745\", \"0.0255\"]", "clobTokenIds": "[\"111\", \"222\"]",
             "volume": 53_000_000},
            {"question": "One cut", "closed": False, "negRisk": True,
             "outcomePrices": "[\"0.02\", \"0.98\"]", "clobTokenIds": "[\"333\", \"444\"]",
             "volume": 1_000},
        ]},
        {"title": "Thin", "slug": "thin", "markets": [
            {"question": "Thin yes", "closed": False, "negRisk": False,
             "outcomePrices": "[\"0.5\", \"0.5\"]", "clobTokenIds": "[\"555\"]", "volume": 100},
        ]},
    ]
    rows = polymarket.macro_odds(events)
    assert [row["question"] for row in rows] == ["No cuts", "One cut"]
    assert rows[0]["prob_yes"] == 0.9745
    assert rows[0]["token_id"] == "111"
    assert rows[1]["token_id"] == "333"


def test_annual_history_keeps_ten_years_and_filing_date():
    def year(end, val, filed):
        return {"form": "10-K", "val": val, "end": end, "start": f"{int(end[:4]) - 1}-09-28", "filed": filed, "fp": "FY"}

    facts = {"facts": {"us-gaap": {
        "Revenues": {"units": {"USD": [year("2024-09-28", 100, "2024-11-01"), year("2025-09-27", 200, "2025-10-31")]}},
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [year("2025-09-27", 80, "2025-10-31")]}},
        "PaymentsToAcquirePropertyPlantAndEquipment": {"units": {"USD": [year("2025-09-27", 30, "2025-10-31")]}},
        "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": [
            {"form": "10-K", "val": 50, "end": "2025-09-27", "filed": "2025-10-31"},
        ]}},
    }, "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [
        {"form": "10-K", "val": 15, "end": "2025-09-27", "filed": "2025-10-31"},
    ]}}}}}
    rows = edgar.annual_history(facts)
    revenue = [row for row in rows if row[0] == "revenue"]
    assert [row[1] for row in revenue] == ["FY2025", "FY2024"]
    assert revenue[0][3] == "2025-10-31"
    fcf = next(row for row in rows if row[0] == "free_cash_flow" and row[1] == "FY2025")
    assert fcf[2] == 50
    assert any(row[0] == "shares_outstanding" and row[2] == 15 for row in rows)


def test_risk_compression_context_is_only_the_filing():
    from signal_chain.data.layer import risk_compression_messages

    messages = risk_compression_messages("ONLY-FILING")
    assert [item["role"] for item in messages] == ["system", "user"]
    assert messages[1]["content"] == "ONLY-FILING"
    assert "200" in messages[0]["content"]
    assert "价格" not in messages[0]["content"]
    assert "财务" not in messages[0]["content"]


def test_risk_excerpt_keeps_full_length_and_prefers_summary():
    short, quality = edgar.risk_excerpt("风险不长")
    assert short == "风险不长" and quality == ""
    capped, quality = edgar.risk_excerpt("x" * 25000)
    assert len(capped) == 20000 and quality == "full=25000"
    summary, quality = edgar.risk_excerpt("x" * 25000, "供应链中断")
    assert summary == "供应链中断" and quality == "summary full=25000"


def test_10k_uses_the_long_item_not_the_table_of_contents():
    toc = "Item 1. Business 1 Item 1A. Risk Factors 2 Item 1B. Unresolved Staff Comments 3 "
    body = (
        "Item 1. Business The company sells devices and services to a global installed base. "
        "Competition The company competes with other smartphone makers across hardware and services worldwide. "
        "Item 1A. Risk Factors Supply concentration can interrupt production for months. "
        "Item 1B. Unresolved Staff Comments None here."
    )
    sections = edgar.excerpts_from_10k(toc + body)
    text, quality = sections["competition"]
    assert "smartphone" in text
    assert "Item 1A" not in text
    assert quality == "extraction_suspect"
    assert "sells devices" in sections["business"][0]
    assert "Supply concentration" in sections["risk_factors"][0]


def test_revenue_pair_skips_the_outlier():
    def get(url, headers=None):
        if "income-statement?symbol" in url:
            return [{"revenue": 200, "date": "2025-09-27"}]
        if "companyfacts" in url:
            return {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
                {"form": "10-K", "val": 100.0, "end": "2025-09-27"},
            ]}}}}}
        return _edgar_get(url, headers)

    market = _load(
        futu=_futu(), get=get,         keys={"FMP_API_KEY": "k"}, quota=lambda: True,
    )
    assert market.snapshot.fundamentals.status == "available"
    assert market.snapshot.fundamentals.source == "edgar"
    assert any(row.id == "fmp" and "1%" in row.note for row in market.sources)


def test_revenue_stays_missing_when_no_pair_agrees():
    def get(url, headers=None):
        if "income-statement?symbol" in url:
            return [{"revenue": 200, "date": "2025-09-27"}]
        if "companyfacts" in url:
            return {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
                {"form": "10-K", "val": 100.0, "end": "2025-09-27"},
            ]}}}}}
        return _edgar_get(url, headers)

    market = _load(
        futu=_futu(), get=get,
        keys={"FMP_API_KEY": "k"}, quota=lambda: True,
    )
    assert market.snapshot.fundamentals.status == "available"
    assert market.snapshot.fundamentals.source == "edgar"


def test_fmp_key_alias_from_env_file(tmp_path):
    from signal_chain.data.keys import load_keys

    src = tmp_path / "env"
    src.write_text("FMP_KEY=abc\nEDGAR_CONTACT=a@b.c\n", encoding="utf-8")
    keys = load_keys(src)
    assert keys["FMP_API_KEY"] == "abc"
    assert keys["EDGAR_CONTACT"] == "a@b.c"


def test_latest_revenue_skips_the_stale_tag():
    facts = {"facts": {"us-gaap": {
        "Revenues": {"units": {"USD": [
            {"form": "10-K", "val": 265.0, "end": "2018-09-29", "start": "2017-10-01", "fp": "FY", "frame": "CY2018"},
        ]}},
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
            {"form": "10-K", "val": 416.0, "end": "2025-09-27", "start": "2024-09-29", "fp": "FY", "frame": "CY2025"},
            {"form": "10-K", "val": 62.0, "end": "2025-09-27", "start": "2025-06-28", "fp": "FY", "frame": "CY2025Q4"},
        ]}},
    }}}
    assert edgar.latest_revenue(facts) == (416.0, "FY2025", "2025-09-27")


def test_newer_quarter_is_the_headline():
    def get(url, headers=None):
        if "company_tickers" in url:
            return {"0": {"ticker": "AAPL", "cik_str": 320193}}
        if "companyfacts" in url:
            return {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
                {"form": "10-K", "val": 400.0, "end": "2025-09-27", "start": "2024-09-29", "fp": "FY"},
                {"form": "10-Q", "val": 110.0, "end": "2026-06-27", "start": "2026-03-29", "fp": "Q3"},
            ]}}}}}
        if "submissions" in url:
            return {"filings": {"recent": {"form": ["10-Q"], "filingDate": ["2026-07-31"]}}}
        raise AssertionError(url)

    market = _load(futu=_futu(), get=get)
    assert market.snapshot.fundamentals.status == "available"
    assert market.snapshot.fundamentals.period == "Q2026-06-27"
    assert market.snapshot.fundamentals.source == "edgar"
    revenues = [fact for fact in market.facts if fact.metric == "revenue"]
    assert {fact.period for fact in revenues} == {"FY2025", "Q2026-06-27"}


def test_reddit_keeps_posts_from_the_last_day():
    from datetime import datetime

    from signal_chain.data import reddit
    now = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)
    fresh = int(now.timestamp()) - 3600
    stale = int(now.timestamp()) - 2 * 86400
    payload = {"data": {"children": [
        {"data": {"title": "AAPL new", "created_utc": fresh}},
        {"data": {"title": "AAPL old", "created_utc": stale}},
    ]}}
    assert reddit.recent_titles(payload, now) == ["AAPL new"]


def test_earnings_calendar_parsers():
    nasdaq = {"data": {"rows": [
        {"symbol": "MSFT", "time": "time-pre-market"},
        {"symbol": "AAPL", "time": "time-not-supplied", "fiscalQuarterEnding": "Sep/2026"},
    ]}}
    assert earnings_calendar.nasdaq_hit(nasdaq, "AAPL")["fiscalQuarterEnding"] == "Sep/2026"
    finn = {"earningsCalendar": [
        {"symbol": "AAPL", "date": "2026-10-28", "hour": "amc", "epsEstimate": 1.9, "revenueEstimate": 100},
    ]}
    row = earnings_calendar.finnhub_next(finn, "AAPL")
    assert row["date"] == "2026-10-28"
    assert "EPS预期" in earnings_calendar.estimate_note(row)


def test_parsers():
    assert edgar.cik_for({"0": {"ticker": "AAPL", "cik_str": 32}}, "AAPL") == "0000000032"
    assert fmp.revenue_ttm([{"revenue": 10}]) == 10
    assert fmp.headlines([{"title": "一条"}, {"title": "两条"}]) == "一条；两条"
    assert fmp.daily_probe([{"date": "2026-09-23", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 3}])["quote"]["last"] == 1.5
