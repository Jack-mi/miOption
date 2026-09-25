"""数据层先后兜底。注入假响应，不访问 OpenD 或公网。"""

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from signal_chain.config import NormTicker
from signal_chain.data import eastmoney, edgar, stocktwits
from signal_chain.data.layer import clear_macro_cache, load
from signal_chain.options.underlying_fetch import build_snapshot
from signal_chain.schema.underlying import UnderlyingSnapshot

D0 = date(2026, 9, 23)
NOW = datetime(2026, 9, 23, 20, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _quiet(monkeypatch):
    clear_macro_cache()
    monkeypatch.setattr(stocktwits, "wait_turn", lambda: None)


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


def _states(market, field):
    return {(row.id, row.state) for row in market.sources if row.field == field}


def _load(*, market="US", code="AAPL", futu=None, futu_error=None,
          yahoo=None, yahoo_error=None, keys=None, get=None, info=None, news=None,
          allow_yahoo=False, quota=None, get_text=None):
    ticker = NormTicker(market, code)

    def futu_probe(*_a, **_k):
        return futu, futu_error

    def yahoo_probe(*_a, **_k):
        if not allow_yahoo:
            raise AssertionError("yahoo 不该被调用")
        return yahoo, yahoo_error

    def getter(url, headers=None):
        if get:
            return get(url, headers)
        raise AssertionError(url)

    return load(
        ticker, D0, object(), include_chain=False,
        keys=keys or {},
        get=getter,
        quota=quota or (lambda: False),
        futu_probe=futu_probe,
        yahoo_probe=yahoo_probe,
        yahoo_info=lambda _t: info or {},
        yahoo_news=lambda _t: news or [],
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


def test_fresh_futu_skips_yahoo_and_alpha():
    market = _load(futu=_futu(), get=_edgar_get)
    assert market.snapshot.quote.meta.source == "futu"
    assert market.snapshot.kline.meta.source == "futu"
    assert ("yfinance", "skipped") in _states(market, "quote")
    assert ("alphavantage", "skipped") in _states(market, "quote")
    assert ("futu", "used") in _states(market, "capital_flow")
    assert ("eastmoney", "skipped") in _states(market, "capital_flow")
    assert market.snapshot.fundamentals.status == "missing"
    assert market.facts and market.facts[0].source == "edgar"
    assert market.snapshot.earnings_date is None
    assert any(row.id == "edgar" and row.state == "used" and "申报日 2026-08-01" in row.note
               for row in market.sources if row.field == "earnings")
    assert ("alphavantage", "skipped") in _states(market, "macro")
    assert ("nyfed", "skipped") not in _states(market, "macro")
    assert ("polymarket", "skipped") in _states(market, "events")


def test_yahoo_fills_when_futu_misses():
    def get(url, headers=None):
        if "stocktwits" in url:
            return {"messages": [{"body": "看多"}]}
        if "sec.gov" in url:
            raise RuntimeError("edgar 暂停")
        raise AssertionError(url)

    market = _load(
        futu=None, futu_error="opend 未连接",
        yahoo=_futu(90, flow=False), allow_yahoo=True, get=get,
        news=[{"title": "Yahoo 标题"}],
    )
    assert market.snapshot.quote.meta.source == "yfinance"
    assert "opend 未连接" in (market.snapshot.quote.meta.error or "")
    assert ("alphavantage", "skipped") in _states(market, "quote")
    assert market.snapshot.news.source == "yfinance"
    assert market.snapshot.news.status == "available"
    assert market.news_text == "Yahoo 标题"
    assert any(item.source == "stocktwits" for item in market.social)


def test_alpha_vantage_price_when_both_fail():
    def get(url, headers=None):
        if "TIME_SERIES_DAILY" in url:
            return {"Time Series (Daily)": {
                "2026-09-19": {
                    "1. open": "10", "2. high": "11", "3. low": "9",
                    "4. close": "10", "5. volume": "1",
                },
                D0.isoformat(): {
                    "1. open": "10", "2. high": "12", "3. low": "9",
                    "4. close": "11", "5. volume": "2",
                },
            }}
        if "OVERVIEW" in url:
            return {"RevenueTTM": "100"}
        if "NEWS_SENTIMENT" in url:
            return {"feed": [{"title": "AV 新闻"}]}
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
        yahoo=None, yahoo_error="429", allow_yahoo=True,
        keys={"ALPHAVANTAGE_API_KEY": "k"}, get=get, quota=lambda: True,
    )
    assert market.snapshot.quote.meta.source == "alphavantage"
    assert market.snapshot.quote.last == 11.0
    assert market.snapshot.news.source == "alphavantage"
    assert market.snapshot.fundamentals.status == "available"
    assert {item.source for item in market.social} == {"stocktwits"}


def test_hk_capital_flow_falls_back_to_eastmoney():
    def get(url, headers=None):
        if "fflow" in url:
            return {"data": {"klines": ["2026-09-23,88.5,1"]}}
        raise AssertionError(url)

    market = _load(
        market="HK", code="00700", futu=_futu(flow=False), get=get,
        info={"totalRevenue": 50, "earningsDate": "2026-11-12"},
    )
    assert market.snapshot.capital_flow.status == "available"
    assert market.snapshot.capital_flow.source == "eastmoney"
    assert market.flow_net == 88.5
    assert ("eastmoney", "used") in _states(market, "capital_flow")
    assert market.snapshot.earnings_source == "yfinance"


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


def test_macro_falls_back_to_nyfed_when_rate_missing():
    def get(url, headers=None):
        if "FEDERAL_FUNDS_RATE" in url:
            return {"Note": "no rate"}
        if "function=CPI" in url:
            return {"data": [{"date": "2026-08-01", "value": "2.7"}, {"date": "2026-07-01", "value": "."}]}
        if "function=UNEMPLOYMENT" in url:
            return {"data": [{"date": "2026-08-01", "value": "4.2"}]}
        if "newyorkfed.org" in url:
            return {"refRates": [{"effectiveDate": "2026-09-22", "percentRate": 3.88}]}
        if "sec.gov" in url or "stocktwits" in url:
            return _edgar_get(url, headers)
        raise AssertionError(url)

    market = _load(futu=_futu(), keys={"ALPHAVANTAGE_API_KEY": "k"}, get=get, quota=lambda: True)
    by_series = {point.series: point for point in market.macro}
    assert by_series["CPI"].as_of == date(2026, 8, 1)
    assert by_series["CPI"].value == 2.7
    assert by_series["CPI"].source == "alphavantage"
    assert by_series["UNEMPLOYMENT"].as_of == date(2026, 8, 1)
    assert by_series["FEDERAL_FUNDS_RATE"].source == "nyfed"
    assert by_series["FEDERAL_FUNDS_RATE"].value == 3.88
    assert ("nyfed", "used") in _states(market, "macro")
    from signal_chain.decision.pack import render_pack
    assert "FEDERAL_FUNDS_RATE" in render_pack(market)
    assert "3.88" in render_pack(market)


def test_us_earnings_date_comes_from_yahoo():
    market = _load(
        futu=_futu(), get=_edgar_get, info={"earningsDate": "2026-10-29"},
    )
    assert market.snapshot.earnings_date == date(2026, 10, 29)
    assert market.snapshot.earnings_source == "yfinance"
    assert any("申报日 2026-08-01" in row.note for row in market.sources if row.field == "earnings")


def test_hk_news_uses_ta_format():
    seen = []

    def get(url, headers=None):
        seen.append(url)
        if "NEWS_SENTIMENT" in url:
            return {"feed": [{"title": "港股标题"}]}
        if "function=FEDERAL_FUNDS_RATE" in url or "function=CPI" in url or "function=UNEMPLOYMENT" in url:
            return {"data": [{"date": "2026-08-01", "value": "1"}]}
        raise AssertionError(url)

    market = _load(
        market="HK", code="00700", futu=_futu(),
        keys={"ALPHAVANTAGE_API_KEY": "k"}, get=get, quota=lambda: True,
    )
    assert any("tickers=0700.HK" in url for url in seen)
    assert market.snapshot.news.source == "alphavantage"


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
        if "arctic-shift" in url:
            return {"data": [{
                "title": "AAPL 讨论",
                "created_utc": int(datetime(2026, 9, 20, tzinfo=timezone.utc).timestamp()),
            }]}
        if "stocktwits" in url:
            return {"messages": []}
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
        info={
            "returnOnEquity": 0.1, "freeCashflow": 20, "interestCoverage": 4,
            "earningsDate": "2026-10-29",
        },
    )
    by_metric = {item.metric: item for item in market.ratios}
    assert by_metric["roe"].value == 0.1
    assert by_metric["roe"].source == "edgar,yfinance"
    assert by_metric["free_cash_flow"].value == 20
    assert by_metric["interest_coverage"].value == 4
    assert {item.section for item in market.excerpts} == {"business", "risk_factors", "governance"}
    assert any(item.source == "arctic-shift" for item in market.social)
    from signal_chain.research.workflow import role_gap_labels, role_memo
    assert "sells devices" in role_memo(market)
    assert "商业模式缺失" not in role_gap_labels(market)
    assert "竞争缺失" in role_gap_labels(market)
    text = render_pack(market)
    assert "商业模式" in text and "sells devices" in text
    assert "竞争缺失" in text
    assert "risk_factors" in text
    assert "宏观缺失" in text


def test_stale_archive_is_not_current_social():
    def get(url, headers=None):
        if "arctic-shift" in url:
            return {"data": [{"title": "旧帖", "created_utc": 1_600_000_000}]}
        return _edgar_get(url, headers)

    market = _load(futu=_futu(), get=get)
    assert all(item.source != "arctic-shift" for item in market.social)
    assert ("arctic-shift", "stale") in _states(market, "social")


def test_10k_competition_heading_becomes_excerpt():
    html = (
        "Item 1. Business The company sells devices and services to a global installed base. "
        "Competition The company competes with other smartphone makers across hardware and services worldwide. "
        "Item 1A. Risk Factors Supply concentration can interrupt production for months. "
        "Item 1B. Unresolved Staff Comments None here."
    )
    sections = edgar.excerpts_from_10k(html)
    assert "smartphone" in sections["competition"]
    assert "Item 1A" not in sections["competition"]


def test_parsers():
    assert edgar.cik_for({"0": {"ticker": "AAPL", "cik_str": 32}}, "AAPL") == "0000000032"
    assert eastmoney.net_inflow({"data": {"klines": ["2026-09-23,3.5"]}}) == ("2026-09-23", 3.5)
    assert eastmoney.net_inflow({"data": {}}) is None
    assert eastmoney.revenue({"result": {"data": [
        {"OPERATE_INCOME": "10", "REPORT_DATE": "2025-12-31"},
    ]}}) == (10.0, "FY2025")
