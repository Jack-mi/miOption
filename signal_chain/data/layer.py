"""数据层唯一入口。价格、新闻、期权链上一级可用就停。财务把候选源取齐后再挑一对。"""

from __future__ import annotations

import contextlib
import io
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ..config import SUPPORTED_HK, NormTicker, Settings
from ..options.chain_fetch import fetch_chain
from ..options.underlying_fetch import (
    build_snapshot,
    probe_futu,
)
from ..sessions import align_futu_quote, session_for
from ..research.berkshire import _cross_validate, attach_fundamentals, note_earnings
from ..schema.underlying import FieldMeta
from . import cboe, daily_store, earnings_calendar, edgar, finnhub, fmp, fred, macro, nasdaq, polymarket, reddit, underlying_store
from .http import get_json, get_text
from .keys import load_keys
from .models import (
    EventOdds, Fact, FilingExcerpt, MacroPoint, MarketData, Ratio, SocialItem, SourceRow,
)

# 取源顺序是 source of truth。新增源必须先登记在这里，再接入级联。
SOURCE_ORDER = {
    "quote": ("futu", "fmp", "nasdaq"),
    "kline": ("futu", "fmp", "nasdaq"),
    "chain": ("futu", "cboe"),
    "earnings": ("nasdaq", "finnhub", "edgar"),
    "fundamentals": ("edgar", "fmp"),
    "news": ("finnhub",),
    "social": ("reddit",),
    "macro": ("supabase",),
}

_NASDAQ_HEADERS = {"User-Agent": "mioption data", "Accept": "application/json"}


def _row(source: str, field: str, state: str, note: str = "") -> SourceRow:
    return SourceRow(source, field, state, note)


def _meta(status: str, source: str | None, as_of: date | None, fetched_at: datetime,
          error: str | None = None, period: str | None = None) -> FieldMeta:
    return FieldMeta(
        status=status, source=source, as_of=as_of, fetched_at=fetched_at,
        error=error, period=period,
    )


def _probe_from_snapshot(snap) -> dict:
    probe: dict = {}
    if snap.quote.meta.status == "available" and snap.quote.last is not None:
        probe["quote"] = {
            "last": snap.quote.last,
            "session_date": snap.quote.meta.as_of.isoformat() if snap.quote.meta.as_of else None,
            "update_time": snap.quote.meta.market_time,
            "observed_at": snap.quote.meta.fetched_at.isoformat() if snap.quote.meta.fetched_at else None,
            "error": None,
        }
    if snap.kline.meta.status == "available" and snap.kline.bars:
        probe["kline"] = {
            "adjusted": snap.kline.adjusted,
            "bars": [
                {
                    "trade_date": bar.trade_date.isoformat(),
                    "open": bar.open, "high": bar.high, "low": bar.low,
                    "close": bar.close, "volume": bar.volume,
                }
                for bar in snap.kline.bars
            ],
            "error": None,
        }
    return probe


def _price_rows(snap, tried: dict[str, str]) -> list[SourceRow]:
    rows = []
    for field, meta in (("quote", snap.quote.meta), ("kline", snap.kline.meta)):
        winner = meta.source
        for source in SOURCE_ORDER[field]:
            if winner == source and meta.status == "available":
                rows.append(_row(source, field, "used"))
            elif winner == source and meta.status == "stale":
                rows.append(_row(source, field, "stale", meta.error or "stale"))
            elif source in tried and tried[source] == "skipped":
                rows.append(_row(source, field, "skipped", "上一级已可用"))
            elif source in tried:
                rows.append(_row(source, field, "missing", tried[source]))
            elif source == "futu" and meta.status != "available":
                rows.append(_row("futu", field, "missing", meta.error or meta.status))
            elif source not in tried:
                rows.append(_row(source, field, "skipped", "上一级已可用"))
    if snap.technical.meta.status == "available":
        rows.append(_row("local_technical", "technical", "used", snap.technical.meta.source or ""))
    else:
        rows.append(_row("local_technical", "technical", "missing", snap.technical.meta.error or ""))
    return rows


def _flow_meta(raw: dict | None, source: str, fetched_at: datetime) -> FieldMeta:
    if not raw or raw.get("net") is None or not raw.get("as_of"):
        return _meta("missing", source, None, fetched_at, (raw or {}).get("error") or "无净流入")
    return _meta("available", source, date.fromisoformat(str(raw["as_of"])[:10]), fetched_at)


def _news_meta(text: str | None, source: str, as_of: date, fetched_at: datetime, error: str | None) -> FieldMeta:
    if text:
        return _meta("available", source, as_of, fetched_at)
    return _meta("missing", source, None, fetched_at, error or "无标题")


def load_macro(keys: dict[str, str], today: date, get=get_json, quota=None) -> tuple[list[MacroPoint], list[SourceRow]]:
    """宏观只读共享层。刷新由 macro_refresh 单独负责，不在这里发 FRED 请求。"""
    return macro.read_macro(keys.get("SUPABASE_SERVICE_ROLE_KEY"), get=get)


def _completed_session(session: date, fetched_at: datetime) -> date:
    from ..sessions import _calendar, _previous_session

    local_day = fetched_at.astimezone(ZoneInfo("America/New_York")).date()
    close = _calendar().session_close(session).to_pydatetime()
    return _previous_session(session) if local_day == session and fetched_at < close else session


def _history_start(prior: list[dict], completed: date, trade_date: date) -> date:
    if not prior:
        return trade_date - timedelta(days=120)
    from ..sessions import _calendar

    known = {str(bar["trade_date"])[:10] for bar in prior}
    first = date.fromisoformat(min(known))
    missing = next((day.date() for day in _calendar().sessions_in_range(first, completed)
                    if day.date().isoformat() not in known), None)
    return (missing or date.fromisoformat(max(known))) - timedelta(days=7)


def _completed_bars(probe: dict, completed: date) -> dict:
    kline = probe.get("kline") or {}
    return {**probe, "kline": {**kline, "bars": [bar for bar in kline.get("bars") or []
            if str(bar.get("trade_date") or "")[:10] <= completed.isoformat()]}}


def _price_and_flow(t, trade_date, settings, fetched_at, keys, get, quota, futu_probe):
    """报价和日线按 SOURCE_ORDER 级联。资金流只用这次富途探测。"""
    tried: dict[str, str] = {}
    history = None
    session = session_for(t.market, trade_date, now=fetched_at)
    completed = _completed_session(session, fetched_at) if t.market == "US" else session
    if futu_probe is probe_futu:
        history = daily_store.DailyStore()
        prior = history.read(t.canonical, "futu", True, completed)
        start = _history_start(prior, completed, trade_date)
        futu, futu_error = futu_probe(t, trade_date, settings, history_start=start)
        if futu:
            futu = _completed_bars(futu, completed)
            fresh_bars = futu["kline"]["bars"]
            if fresh_bars and not futu_error and not (futu.get("kline") or {}).get("error"):
                history.save(t.canonical, "futu", True, fresh_bars, completed, fetched_at)
                merged = {str(bar["trade_date"])[:10]: bar for bar in prior}
                merged.update({str(bar["trade_date"])[:10]: bar for bar in fresh_bars})
                futu = {**futu, "kline": {**futu["kline"],
                                        "bars": [merged[day] for day in sorted(merged)]}}
    else:
        futu, futu_error = futu_probe(t, trade_date, settings)
    if t.market == "US":
        futu = align_futu_quote(futu)
    tried["futu"] = futu_error or "ok"
    from ..options.underlying_fetch import _futu_field_fresh
    fresh = _futu_field_fresh(futu, session, "quote") and _futu_field_fresh(futu, completed, "kline")
    snap = build_snapshot(
        ticker=t.canonical, market=t.market, trade_date=trade_date, fetched_at=fetched_at,
        futu=futu, futu_error=futu_error, kline_session=completed,
    )
    if fresh:
        tried["fmp"] = "skipped"
    elif not keys.get("FMP_API_KEY"):
        tried["fmp"] = "skipped"
    elif not quota():
        tried["fmp"] = "当日额度用尽"
    else:
        tried["fmp"] = "ok"
        url = fmp.endpoint("historical-price-eod/full", keys["FMP_API_KEY"], symbol=t.code)
        try:
            payload = get(url)
            limited = fmp.note(payload)
            probe = None if limited else fmp.daily_probe(payload)
            if probe is None:
                tried["fmp"] = limited or "无日线"
            else:
                probe = _completed_bars(probe, completed)
                snap = build_snapshot(
                    ticker=t.canonical, market=t.market, trade_date=trade_date,
                    fetched_at=fetched_at,
                    futu=_probe_from_snapshot(snap),
                    fallback=probe,
                    futu_error=snap.quote.meta.error,
                    fallback_source="fmp",
                    kline_session=completed,
                )
        except Exception as exc:
            tried["fmp"] = fmp.public_error(exc)
    both_available = snap.quote.meta.status == "available" and snap.kline.meta.status == "available"
    used_nasdaq = any(
        meta.source == "nasdaq" and meta.status == "available"
        for meta in (snap.quote.meta, snap.kline.meta)
    )
    if both_available and not used_nasdaq:
        tried["nasdaq"] = "skipped"
    else:
        tried["nasdaq"] = "ok"
        url = nasdaq.historical_url(t.code, trade_date - timedelta(days=14), trade_date)
        try:
            probe = nasdaq.daily_probe(get(url, _NASDAQ_HEADERS))
            if probe is None:
                tried["nasdaq"] = "无日线"
            else:
                probe = _completed_bars(probe, completed)
                snap = build_snapshot(
                    ticker=t.canonical, market=t.market, trade_date=trade_date,
                    fetched_at=fetched_at,
                    futu=_probe_from_snapshot(snap),
                    fallback=probe,
                    futu_error=snap.quote.meta.error,
                    fallback_source="nasdaq",
                    kline_session=completed,
                )
                used_nasdaq = any(
                    meta.source == "nasdaq" and meta.status == "available"
                    for meta in (snap.quote.meta, snap.kline.meta)
                )
                if not used_nasdaq:
                    tried["nasdaq"] = "无这场日线"
        except Exception as exc:
            tried["nasdaq"] = nasdaq.public_error(exc)
    rows = _price_rows(snap, tried)
    snap, flow_rows, flow_net = _capital_flow(snap, futu, fetched_at)
    rows.extend(flow_rows)
    return snap, rows, flow_net


def _option_chain(t, trade_date, settings, chain_fetch, get):
    rows: list[SourceRow] = []
    try:
        chain = chain_fetch(t, settings)
    except Exception as exc:
        futu_error = str(exc)[:300]
        rows.append(_row("futu", "chain", "missing", futu_error or "富途不可用"))
        if os.environ.get("MIOPTION_CBOE_PROGRAMMATIC_LICENSE") != "confirmed":
            rows.append(_row("cboe", "chain", "skipped", "程序化使用许可未确认"))
            return None, f"futu: {futu_error}；cboe: 程序化使用许可未确认", rows
        try:
            chain = cboe.fetch_chain(t, trade_date, settings, get)
        except Exception as exc:
            chain_error = f"futu: {futu_error}；cboe: {str(exc)[:160]}"
            rows.append(_row("cboe", "chain", "missing", str(exc)[:160]))
            return None, chain_error, rows
        rows.append(_row("cboe", "chain", "used", "Futu 失败后降级"))
        return chain, None, rows
    rows.append(_row("futu", "chain", "used"))
    rows.append(_row("cboe", "chain", "skipped", "上一级已可用"))
    return chain, None, rows


def _hk_facts(financials: dict | None) -> tuple[list[Fact], list[Ratio]]:
    facts: list[Fact] = []
    ratios: list[Ratio] = []
    if not financials or financials.get("error"):
        return facts, ratios
    period = str(financials.get("period") or "")
    filed = str(financials.get("as_of") or "")
    income = financials.get("income") or {}
    for metric, key in (
        ("revenue", "revenue"), ("gross_profit", "gross_profit"),
        ("operating_profit", "operating_profit"), ("net_profit", "net_profit"),
        ("net_profit_parent", "net_profit_parent"), ("basic_eps", "basic_eps"),
        ("diluted_eps", "diluted_eps"),
    ):
        value = income.get(key)
        if value is not None:
            facts.append(Fact("futu_financials", metric, period, float(value), filed))
    metrics = financials.get("metrics") or {}
    metric_period = str(metrics.get("period") or period)
    for metric, key in (
        ("gross_margin", "gross_margin"), ("operating_margin", "operating_margin"),
        ("net_margin", "net_margin"), ("roe", "roe"), ("roa", "roa"),
        ("current_ratio", "current_ratio"), ("quick_ratio", "quick_ratio"),
        ("inventory_turnover", "inventory_turnover"),
    ):
        value = metrics.get(key)
        if value is not None:
            ratios.append(Ratio(metric, float(value), metric_period, "futu_financials"))
    valuation = financials.get("valuation") or {}
    valuation_period = "TTM"
    for metric, key in (
        ("market_cap", "market_cap"), ("pe_ttm", "pe_ttm"), ("pb", "pb"),
        ("dividend_ttm", "dividend_ttm"), ("dividend_yield_ttm", "dividend_yield_ttm"),
    ):
        value = valuation.get(key)
        if value is not None:
            facts.append(Fact("futu_snapshot", metric, valuation_period, float(value),
                              str(valuation.get("as_of") or "")))
    return facts, ratios


def _hk_excerpts(research: dict | None) -> list[FilingExcerpt]:
    if not research or research.get("error") or not research.get("sections"):
        return []
    try:
        as_of = date.fromisoformat(str(research.get("as_of"))[:10])
    except ValueError:
        as_of = None
    source = str(research.get("source") or "futu_morningstar")
    return [
        FilingExcerpt(str(section), str(text), source, as_of, "futu_research")
        for section, text in research["sections"].items() if text
    ]


def _hk_news(news: list | None) -> str | None:
    rows = [row for row in (news or []) if row.get("title")]
    if not rows:
        return None
    return "\n".join(
        f"{row['title']}（{row.get('source') or 'futu_news'}，{row.get('published') or '无日期'}）"
        for row in rows
    )


def _load_hk(
    t: NormTicker,
    trade_date: date,
    settings: Settings,
    *,
    include_chain: bool,
    keys: dict[str, str],
    get,
    futu_probe,
    chain_fetch,
    fetch_macro=None,
) -> MarketData:
    fetched_at = datetime.now(timezone.utc)
    futu, futu_error = futu_probe(t, trade_date, settings)
    snap = build_snapshot(
        ticker=t.canonical, market=t.market, trade_date=trade_date, fetched_at=fetched_at,
        futu=futu, futu_error=futu_error,
    )
    snap, flow_rows, flow_net = _capital_flow(snap, futu, fetched_at)
    facts, ratios = _hk_facts((futu or {}).get("financials"))
    excerpts = _hk_excerpts((futu or {}).get("research"))
    news_text = _hk_news((futu or {}).get("news"))
    rows = [*_price_rows(snap, {"futu": futu_error or "ok"}), *flow_rows]
    if snap.fundamentals.status == "available":
        rows.append(_row("futu_financials", "fundamentals", "used", snap.fundamentals.period or ""))
    else:
        rows.append(_row("futu_financials", "fundamentals", "missing", snap.fundamentals.error or "无财务报表"))
    if news_text:
        rows.append(_row("futu_news", "news", "used"))
    else:
        rows.append(_row("futu_news", "news", "missing", "Futu 无新闻"))
    if excerpts:
        rows.append(_row("futu_morningstar", "filing", "used",
                          f"研究更新 {excerpts[0].as_of.isoformat() if excerpts[0].as_of else '未知'}"))
    else:
        rows.append(_row("futu_morningstar", "filing", "missing", "Futu 无研究摘要"))
    rows.append(_row("futu_earnings", "earnings", "missing", "未确认下一次财报日"))
    rows.append(_row("reddit", "social", "unsupported", "港股本轮不接 Reddit"))

    with ThreadPoolExecutor(max_workers=3) as pool:
        events_f = pool.submit(_events, t, get, fetch_macro)
        macro_f = pool.submit(load_macro, keys, trade_date, get)
        chain_f = pool.submit(
            _option_chain, t, trade_date, settings, chain_fetch, get,
        ) if include_chain else None
        events, event_rows = events_f.result()
        macro, macro_rows = macro_f.result()
        chain_result = chain_f.result() if chain_f else (None, None, [])
    chain, chain_error, chain_rows = chain_result
    if chain is not None:
        if snap.quote.meta.status == "available" and snap.quote.last is not None:
            chain = chain.model_copy(update={
                "spot": snap.quote.last, "spot_at": snap.quote.meta.market_time,
                "spot_fetched_at": snap.quote.meta.fetched_at.isoformat() if snap.quote.meta.fetched_at else None,
            })
        else:
            chain = chain.model_copy(update={"spot": None, "spot_at": None, "degraded": True})
    rows.extend([*event_rows, *macro_rows, *chain_rows])
    return MarketData(
        snap, chain, chain_error, macro, [], events, facts, rows,
        flow_net if snap.capital_flow.status == "available" else None,
        news_text if snap.news.status == "available" else None,
        ratios, excerpts, False,
    )


def load(
    t: NormTicker,
    trade_date: date,
    settings: Settings,
    *,
    include_chain: bool = True,
    keys: dict[str, str] | None = None,
    get=get_json,
    quota=None,
    futu_probe=probe_futu,
    chain_fetch=fetch_chain,
    get_text=get_text,
    fetch_macro=None,
    evidence_store: underlying_store.UnderlyingStore | None = None,
    slow_only: bool = False,
) -> MarketData:
    keys = keys if keys is not None else load_keys()
    fetched_at = datetime.now(timezone.utc)
    if t.market == "HK":
        if t.canonical not in SUPPORTED_HK:
            skeleton = build_snapshot(
                ticker=t.canonical, market=t.market, trade_date=trade_date, fetched_at=fetched_at,
            )
            return MarketData(
                skeleton, None, "只覆盖美股和指定港股", [], [], [], [],
                [_row("loader", "market", "unsupported", "港股 allowlist 之外")],
                None, None, [], [],
            )
        return _load_hk(
            t, trade_date, settings, include_chain=include_chain, keys=keys, get=get,
            futu_probe=futu_probe, chain_fetch=chain_fetch, fetch_macro=fetch_macro,
        )
    if t.market != "US":
        raise ValueError("只覆盖美股和指定港股")
    quota = quota or (lambda: fmp.take_quota(trade_date))
    store = evidence_store or (underlying_store.UnderlyingStore(keys["SUPABASE_SERVICE_ROLE_KEY"])
                               if keys.get("SUPABASE_SERVICE_ROLE_KEY") else None)
    evidence = {category: [] for category in underlying_store.CATEGORIES}
    refresh: dict = {}
    persisted = True
    store_error = None
    if store is not None:
        try:
            evidence, refresh = store.read(t.canonical)
        except Exception as exc:
            persisted = False
            store_error = f"共享标的库不可用: {str(exc)[:120]}"
    else:
        persisted = False
        store_error = "共享标的库缺少凭据"

    skeleton = build_snapshot(
        ticker=t.canonical, market=t.market, trade_date=trade_date, fetched_at=fetched_at,
    )

    def cached(category):
        return persisted and underlying_store.usable(category, refresh.get(category),
                    evidence[category], fetched_at, day=trade_date)

    def throttled(category):
        return persisted and not underlying_store.due(category, refresh.get(category),
                    evidence[category], fetched_at, day=trade_date)

    def fundamentals_job():
        if cached("fundamentals"):
            facts, ratios, meta = underlying_store.facts_from(evidence["fundamentals"], trade_date)
            if meta.status == "available":
                return (skeleton.model_copy(update={"fundamentals": meta}),
                        [underlying_store.used("fundamentals", facts)], facts, ratios)
        if throttled("fundamentals"):
            return skeleton, [_row("supabase", "fundamentals", "stale", "上次失败，等待重试")], [], []
        return _fundamentals(t, skeleton, trade_date, fetched_at, keys, get, quota, cik)

    identity = underlying_store.current(evidence["company"], day=trade_date)
    company_cached = cached("company") and bool(identity)
    company = identity[0]["payload"] if identity else None
    company_fresh = company_cached
    company_error = None
    if not company_cached and not throttled("company"):
        try:
            tickers = get("https://www.sec.gov/files/company_tickers.json",
                          edgar.user_agent(keys.get("EDGAR_CONTACT", "")))
            company = next(({"cik": str(row["cik_str"]).zfill(10),
                             "ticker": t.code, "name": str(row.get("title") or "")}
                            for row in tickers.values() if isinstance(row, dict) and
                            str(row.get("ticker") or "").upper() == t.code), None)
            company_fresh = bool(company)
            if not company:
                company_error = "SEC company_tickers 缺少标的"
        except Exception as exc:
            company_error = str(exc)[:160]
        if not company_fresh and identity:
            company = identity[0]["payload"]
    cik = (company or {}).get("cik")

    filing_cached = cached("filing")
    filing_throttled = throttled("filing") and not filing_cached
    earnings_throttled = throttled("earnings") and not cached("earnings")
    old_excerpts = (underlying_store.excerpts_from(evidence["filing"], trade_date)
                    if filing_cached else [])
    old_earnings = (underlying_store.earnings_from(evidence["earnings"], trade_date)
                    if persisted and cached("earnings") else (None, None))

    def chain_job():
        if not include_chain or slow_only:
            return None, None, []
        return _option_chain(t, trade_date, settings, chain_fetch, get)

    with ThreadPoolExecutor(max_workers=8) as pool:
        price_f = None if slow_only else pool.submit(
            _price_and_flow, t, trade_date, settings, fetched_at, keys, get, quota,
            futu_probe,
        )
        fund_f = pool.submit(fundamentals_job)
        earn_f = pool.submit(_earnings, t, skeleton, trade_date, fetched_at, keys, get, get_text,
                             old_excerpts or None, old_earnings, filing_cached, cik,
                             filing_throttled, earnings_throttled)
        news_f = None if slow_only else pool.submit(
            _news, t, session_for(t.market, trade_date, now=fetched_at), skeleton, trade_date, fetched_at, keys, get,
        )
        social_f = None if slow_only else pool.submit(_social, t, keys, get, trade_date)
        events_f = None if slow_only else pool.submit(_events, t, get, fetch_macro)
        macro_f = None if slow_only else pool.submit(load_macro, keys, trade_date, get)
        chain_f = pool.submit(chain_job)
        snap, price_rows, flow_net = price_f.result() if price_f else (skeleton, [], None)
        fund_snap, fact_rows, facts, ratios = fund_f.result()
        earn_snap, earn_rows, excerpts = earn_f.result()
        news_snap, news_rows, news_text = news_f.result() if news_f else (skeleton, [], None)
        social, social_rows = social_f.result() if social_f else ([], [])
        events, event_rows = events_f.result() if events_f else ([], [])
        macro, macro_rows = macro_f.result() if macro_f else ([], [])
        chain, chain_error, chain_rows = chain_f.result()

    if fund_snap.fundamentals.status != "available" and persisted and evidence["fundamentals"]:
        previous_facts, previous_ratios, previous_meta = underlying_store.facts_from(
            evidence["fundamentals"], trade_date)
        if previous_meta.status == "available":
            facts, ratios = previous_facts, previous_ratios
            fact_rows.append(_row("supabase", "fundamentals", "stale",
                                  "刷新失败，历史证据仅作背景，不参与本轮财务可用判断"))
    filing_stale = not filing_cached and not excerpts and persisted and bool(evidence["filing"])
    if filing_stale:
        excerpts = underlying_store.excerpts_from(evidence["filing"], trade_date)
        if excerpts:
            earn_rows.append(_row("supabase", "filing", "stale", "刷新失败，沿用有出处的旧摘录"))

    stale_evidence = any(row.state == "stale" and row.field in {"fundamentals", "filing"}
                         for row in (*fact_rows, *earn_rows))
    unpersisted_fundamentals = fund_snap.fundamentals.status == "available" and not (
        cached("fundamentals") or underlying_store.evidence_rows(
            "fundamentals", (facts, ratios), fetched_at))
    stale_company = bool(identity) and not company_fresh

    if store is not None and persisted:
        for category, data, report_rows in (
            ("company", company if company_fresh else None, []),
            ("fundamentals", (facts, ratios), fact_rows),
            ("filing", excerpts, earn_rows),
            ("earnings", (earn_snap.earnings_date, earn_snap.earnings_source), earn_rows),
        ):
            if throttled(category) and not cached(category):
                continue
            if (category == "company" and company_cached) or (
                category == "fundamentals" and any(row.id == "supabase" and row.field == category
                                                     for row in fact_rows)) or (category == "filing" and filing_cached) or (
                category == "earnings" and old_earnings[0]):
                continue
            records = [] if (category == "fundamentals" and fund_snap.fundamentals.status != "available") or (
                category == "filing" and filing_stale
            ) else underlying_store.evidence_rows(category, data, fetched_at)
            errors = [row.note for row in report_rows if row.state == "missing" and row.field == category]
            if category == "company" and company_error:
                errors.append(company_error)
            if records:
                errors = []
            try:
                store.save(t.canonical, category, records, "; ".join(errors)[:300] or None)
            except Exception as exc:
                persisted = False
                store_error = f"标的证据写入失败: {str(exc)[:120]}"
    if stale_evidence or unpersisted_fundamentals or stale_company:
        persisted = False
        store_error = store_error or ("部分慢变证据仅有旧版，不能作为本轮晋级证据"
                                      if stale_evidence or stale_company else "财务仅有未持久化的来源，不能晋级")
    if store_error:
        chain_rows.append(_row("supabase", "evidence", "missing", store_error))

    # 报价/日线级联选出的 spot 是唯一基准价；期权链只保留链合约，不另立价格。
    if chain is not None:
        if snap.quote.meta.status == "available" and snap.quote.last is not None:
            chain = chain.model_copy(update={"spot": snap.quote.last, "spot_at": snap.quote.meta.market_time,
                                             "spot_fetched_at": snap.quote.meta.fetched_at.isoformat() if snap.quote.meta.fetched_at else None,
                                             "degraded": chain.degraded or snap.quote.meta.source != "futu"})
        else:
            chain = chain.model_copy(update={"spot": None, "spot_at": None, "degraded": True})

    snap = snap.model_copy(update={
        "fundamentals": fund_snap.fundamentals,
        "news": news_snap.news,
        "earnings_date": earn_snap.earnings_date,
        "earnings_source": earn_snap.earnings_source,
    })
    rows = [
        *price_rows, *fact_rows, *earn_rows, *news_rows, *social_rows,
        *event_rows, *macro_rows, *chain_rows,
    ]
    return MarketData(
        snap, chain, chain_error, macro, social, events, facts, rows,
        flow_net if snap.capital_flow.status == "available" else None,
        news_text if snap.news.status == "available" else None,
        ratios,
        excerpts, persisted,
    )


def _capital_flow(snap, futu, fetched_at):
    raw = (futu or {}).get("capital_flow") if futu else None
    meta = _flow_meta(raw, "futu", fetched_at)
    if meta.status == "available":
        return snap.model_copy(update={"capital_flow": meta}), [_row("futu", "capital_flow", "used")], float(raw["net"])
    err = meta.error or "富途不可用"
    meta = meta.model_copy(update={"error": err})
    return (
        snap.model_copy(update={"capital_flow": meta}),
        [_row("futu", "capital_flow", "missing", err)],
        None,
    )


def _consistent(metric: str, values: dict[str, float]) -> bool:
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return bool(_cross_validate(metric, values)["all_consistent"])
    except Exception:
        return False


def _choose_revenue(values: dict[str, float], rows: list[SourceRow]) -> tuple[dict[str, float], bool]:
    """EDGAR 有数就用 EDGAR。FMP 只在缺 EDGAR 时补上；对不上只告警。"""
    edgar_value = values.get("edgar")
    fmp_value = values.get("fmp")
    if edgar_value is not None and fmp_value is not None:
        pair = {"edgar": edgar_value, "fmp": fmp_value}
        if _consistent("revenue", pair):
            return pair, False
        rows.append(_row("fmp", "fundamentals", "missing", "与 EDGAR 相差超过 1%"))
        return {"edgar": edgar_value}, True
    if edgar_value is not None:
        return {"edgar": edgar_value}, True
    if fmp_value is not None:
        return {"fmp": fmp_value}, True
    return {}, False


def _ratio_candidates(t, facts_payload) -> dict[str, dict[str, tuple[float, str]]]:
    found: dict[str, dict[str, tuple[float, str]]] = {}

    def put(metric: str, source: str, value: float | None, period: str) -> None:
        if value is None:
            return
        found.setdefault(metric, {})[source] = (value, period)

    if t.market == "US" and facts_payload:
        for metric, (value, period) in edgar.derived_ratios(facts_payload).items():
            put(metric, "edgar", value, period)
    return found


def _accept_ratios(candidates: dict[str, dict[str, tuple[float, str]]]):
    prefer = ("edgar",)
    ratios: list[Ratio] = []
    rows: list[SourceRow] = []
    extra: list[Fact] = []
    for metric, sources in candidates.items():
        values = {name: pair[0] for name, pair in sources.items()}
        if len(values) >= 2 and _consistent(metric, values):
            chosen = next(name for name in prefer if name in values)
            joined = ",".join(name for name in prefer if name in values)
            ratios.append(Ratio(metric, values[chosen], sources[chosen][1], joined))
            rows.append(_row(joined, metric, "used", sources[chosen][1]))
        else:
            for name, (value, period) in sources.items():
                extra.append(Fact(name, metric, period, value))
                rows.append(_row(name, metric, "used", "单源"))
    return rows, extra, ratios


def risk_compression_messages(text: str) -> list[dict[str, str]]:
    """压缩环节的全部上下文：系统指令加上 Item 1A 原文。没有行情、财报数字或上一轮对话。"""
    return [
        {
            "role": "system",
            "content": (
                "你是数据链上单独的压缩环节。这次上下文只有下面那份 10-K Item 1A，没有别的材料。"
                "不要编造原文没有的风险。"
                "输出不超过 12 条。每条先写一句判断，换行后写「说明：」，用 200 到 400 字写这一条在原文里的具体情况。"
                "相近的可以合并，但法律、税务、平台和监管也要覆盖到。"
                "不要前言，不要结尾。"
            ),
        },
        {"role": "user", "content": text},
    ]


def _summarize_risk(text: str) -> tuple[str, str]:
    """风险因素全文交给单独一次模型调用。没有钥匙或调用失败时，仍只留前 2 万字，并记下全长。"""
    from ..agents.llm import load_deepseek_key

    key = load_deepseek_key()
    if not key or len(text) <= 4000:
        return edgar.risk_excerpt(text)
    try:
        summary = _risk_summary(text, key)
    except Exception:
        return edgar.risk_excerpt(text)
    return edgar.risk_excerpt(text, summary)


def _risk_summary(text: str, api_key: str) -> str:
    import httpx

    response = httpx.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "deepseek-chat",
            "temperature": 0,
            "max_tokens": 8192,
            "messages": risk_compression_messages(text),
        },
        timeout=180,
    )
    response.raise_for_status()
    return str(response.json()["choices"][0]["message"]["content"]).strip()


def _filing_excerpts(cik: str, submissions: dict, read_text, contact: str) -> list[FilingExcerpt]:
    out: list[FilingExcerpt] = []
    headers = edgar.user_agent(contact)
    annual = edgar.latest_primary(submissions, {"10-K", "20-F"})
    if annual:
        try:
            html = read_text(edgar.archive_url(cik, annual["accession"], annual["document"]), headers)
            filed = date.fromisoformat(annual["filed"])
            for section, (text, quality) in edgar.excerpts_from_10k(html).items():
                if section == "risk_factors" and not quality.startswith("summary"):
                    text, quality = _summarize_risk(text)
                out.append(FilingExcerpt(section, text, "edgar", filed, quality))
        except Exception:
            pass
    proxy = edgar.latest_primary(submissions, {"DEF 14A"})
    if proxy:
        try:
            html = read_text(edgar.archive_url(cik, proxy["accession"], proxy["document"]), headers)
            filed = date.fromisoformat(proxy["filed"])
            for section, text in edgar.excerpts_from_proxy(html).items():
                out.append(FilingExcerpt(section, text, "edgar", filed))
        except Exception:
            pass
    return out


def _period_end(label: str) -> date | None:
    text = label[1:] if label.startswith(("Q", "FY")) and len(label) > 10 else label
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _fundamentals(t, snap, trade_date, fetched_at, keys, get, quota, cik=None):
    facts: list[Fact] = []
    annual_values: dict[str, float] = {}
    annual_periods: dict[str, str] = {}
    annual_ends: list[date] = []
    quarter_values: dict[str, float] = {}
    quarter_periods: dict[str, str] = {}
    quarter_ends: list[date] = []
    period = f"FY{trade_date.year}"
    rows: list[SourceRow] = []
    contact = keys.get("EDGAR_CONTACT", "")
    facts_payload = None

    def keep(bucket: dict[str, float], periods: dict[str, str], ends: list[date], source: str,
             value: float, source_period: str, metric: str, end: date | None, note: str = "") -> None:
        bucket[source] = value
        periods[source] = source_period
        if end is not None:
            ends.append(end)
        facts.append(Fact(source, metric, source_period, value))
        rows.append(_row(source, "fundamentals", "used", note or source_period))

    if t.market == "US":
        symbol = t.code
        try:
            if cik is None:
                tickers = get("https://www.sec.gov/files/company_tickers.json", edgar.user_agent(contact))
                cik = edgar.cik_for(tickers, symbol)
            if cik is None:
                raise ValueError("无 CIK")
            facts_payload = get(
                f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                edgar.user_agent(contact),
            )
            found = edgar.latest_revenue(facts_payload)
        except Exception as exc:
            found = None
            rows.append(_row("edgar", "fundamentals", "missing", str(exc)[:160]))
        if found:
            keep(annual_values, annual_periods, annual_ends, "edgar", found[0], found[1], "revenue",
                 date.fromisoformat(found[2]), found[2])
        quarter = edgar.latest_quarter_revenue(facts_payload) if facts_payload else None
        if quarter is not None:
            keep(quarter_values, quarter_periods, quarter_ends, "edgar", quarter[0], quarter[1], "revenue",
                 _period_end(quarter[1]), quarter[1])
        if facts_payload:
            filed_by_metric_period = {
                (metric, period): filed for metric, period, _value, filed
                in edgar.annual_history(facts_payload) if filed
            }
            for fact in facts:
                if fact.source == "edgar" and not fact.filed:
                    fact.filed = filed_by_metric_period.get((fact.metric, fact.period), "")
            seen = {(item.source, item.metric, item.period) for item in facts}
            added = 0
            for metric, period, value, filed in edgar.annual_history(facts_payload):
                key = ("edgar", metric, period)
                if key in seen:
                    continue
                seen.add(key)
                facts.append(Fact("edgar", metric, period, value, filed))
                added += 1
            if added:
                rows.append(_row("edgar", "fundamentals", "used", f"十年序列 {added}"))
        if not keys.get("FMP_API_KEY"):
            rows.append(_row("fmp", "fundamentals", "skipped", "没有 FMP_API_KEY"))
        elif not quota():
            rows.append(_row("fmp", "fundamentals", "missing", "当日额度用尽"))
        else:
            try:
                payload = get(fmp.endpoint(
                    "income-statement", keys["FMP_API_KEY"], symbol=symbol, period="annual", limit="1",
                ))
                limited = fmp.note(payload)
                parsed = None if limited else fmp.annual_revenue(payload)
                if parsed is None:
                    raise ValueError(limited or "无 revenue")
                keep(annual_values, annual_periods, annual_ends, "fmp", parsed[0], parsed[1], "revenue",
                     date.fromisoformat(parsed[2]), parsed[2])
                quarter = fmp.quarter_revenue(get(fmp.endpoint(
                    "income-statement", keys["FMP_API_KEY"], symbol=symbol, period="quarter", limit="1",
                )))
                if quarter is not None:
                    keep(quarter_values, quarter_periods, quarter_ends, "fmp", quarter[0], quarter[1], "revenue",
                         _period_end(quarter[1]), quarter[1])
            except Exception as exc:
                rows.append(_row("fmp", "fundamentals", "missing", fmp.public_error(exc)))
    else:
        rows.append(_row("edgar", "fundamentals", "unsupported", "只覆盖美股"))
        rows.append(_row("fmp", "fundamentals", "unsupported", "只覆盖美股"))
    ratio_rows, ratio_facts, ratios = _accept_ratios(_ratio_candidates(t, facts_payload))
    rows.extend(ratio_rows)
    have = {(item.metric, item.period) for item in facts}
    facts.extend(fact for fact in ratio_facts if (fact.metric, fact.period) not in have)
    annual_end = max(annual_ends, default=None)
    quarter_end = max(quarter_ends, default=None)
    if quarter_values and quarter_end and (annual_end is None or quarter_end > annual_end):
        values, periods = quarter_values, quarter_periods
    else:
        values, periods = annual_values, annual_periods
    chosen, alone = _choose_revenue(values, rows)
    if chosen:
        period = periods[next(iter(chosen))]
    try:
        snap = attach_fundamentals(
            snap, metric="revenue", period=period, values=chosen,
            as_of=trade_date, fetched_at=fetched_at, require_pair=not alone,
        )
    except Exception as exc:
        snap = snap.model_copy(update={"fundamentals": _meta(
            "missing", None, trade_date, fetched_at, str(exc)[:160])})
    return snap, rows, facts, ratios


def _earnings(t, snap, trade_date, fetched_at, keys, get, read_text,
              cached_excerpts=None, cached_event=(None, None), filing_cached=False, cik=None,
              filing_throttled=False, earnings_throttled=False):
    rows = []
    excerpts: list[FilingExcerpt] = []
    contact = keys.get("EDGAR_CONTACT", "")
    if filing_cached:
        excerpts = cached_excerpts or []
        rows.append(_row("supabase", "filing", "used", "复用有来源时点的申报摘录"))
        if excerpts:
            rows.append(_row("edgar", "earnings", "used",
                             f"申报日 {max(item.as_of for item in excerpts if item.as_of).isoformat()}（共享证据）"))
    elif filing_throttled:
        rows.append(_row("supabase", "filing", "stale", "上次失败，等待重试"))
    elif t.market == "US":
        try:
            if cik is None:
                tickers = get("https://www.sec.gov/files/company_tickers.json", edgar.user_agent(contact))
                cik = edgar.cik_for(tickers, t.code)
            if cik is None:
                raise ValueError("无 CIK")
            submissions = get(
                f"https://data.sec.gov/submissions/CIK{cik}.json",
                edgar.user_agent(contact),
            )
            filed = edgar.latest_filing_date(submissions)
        except Exception as exc:
            rows.append(_row("edgar", "earnings", "missing", str(exc)[:160]))
        else:
            if filed is None:
                rows.append(_row("edgar", "earnings", "missing", "无 10-K/10-Q"))
            else:
                rows.append(_row("edgar", "earnings", "used", f"申报日 {filed.isoformat()}"))
            excerpts = _filing_excerpts(cik, submissions, read_text, contact)
            for item in excerpts:
                if item.section == "risk_factors" and item.quality.startswith("summary"):
                    rows.append(_row("deepseek", "risk_factors", "used", item.quality))
                elif item.section == "risk_factors" and item.quality.startswith("full="):
                    rows.append(_row("deepseek", "risk_factors", "missing", item.quality))
    else:
        rows.append(_row("edgar", "earnings", "unsupported", "港股财报日不走 EDGAR"))
    found, note = ((cached_event, "复用共享财报事件") if cached_event[0]
                   else (None, "上次失败，等待重试") if earnings_throttled
                   else _next_earnings(t.code, trade_date, keys, get))
    if found is None:
        rows.append(_row("nasdaq", "earnings", "missing", note or "日历没有下次财报日"))
        return snap, rows, excerpts
    snap = note_earnings(snap, found[0], source=found[1])
    return snap, rows + [_row(found[1], "earnings", "used", note or found[0].isoformat())], excerpts


def _next_earnings(symbol: str, day: date, keys: dict, get) -> tuple[tuple[date, str] | None, str]:
    """Nasdaq 当天名单为主。Finnhub 给出近月日期和预期，用来对准 Nasdaq 的日期。"""
    hint = None
    hint_note = ""
    if keys.get("FINNHUB_API_KEY"):
        try:
            payload = get(earnings_calendar.finnhub_url(
                symbol, day, day + timedelta(days=31), keys["FINNHUB_API_KEY"],
            ))
            hint = earnings_calendar.finnhub_next(payload, symbol)
            hint_note = earnings_calendar.estimate_note(hint)
        except Exception as exc:
            hint_note = finnhub.public_error(exc)
    days = []
    if hint and hint.get("date"):
        hinted = date.fromisoformat(str(hint["date"])[:10])
        days = [hinted, hinted + timedelta(days=1)]
    else:
        days = earnings_calendar.upcoming_days(day + timedelta(days=1), 24)
    for probe in days:
        try:
            payload = get(earnings_calendar.nasdaq_url(probe), _NASDAQ_HEADERS)
        except TypeError:
            payload = get(earnings_calendar.nasdaq_url(probe))
        except Exception:
            continue
        if earnings_calendar.nasdaq_hit(payload, symbol):
            note = f"Nasdaq {probe.isoformat()}"
            if hint_note:
                note = f"{note}；{hint_note}"
            return (probe, "nasdaq"), note
    if hint and hint.get("date"):
        found = date.fromisoformat(str(hint["date"])[:10])
        return (found, "finnhub"), hint_note or found.isoformat()
    return None, hint_note


def _news(t, session: date, snap, trade_date, fetched_at, keys, get):
    rows = []
    if not keys.get("FINNHUB_API_KEY"):
        rows.append(_row("finnhub", "news", "missing", "没有 FINNHUB_API_KEY"))
    else:
        try:
            payload = get(finnhub.news_url(t.code, session, keys["FINNHUB_API_KEY"]))
            text = finnhub.headlines(payload)
            if text:
                rows.append(_row("finnhub", "news", "used"))
                return snap.model_copy(update={"news": _news_meta(text, "finnhub", session, fetched_at, None)}), rows, text
            rows.append(_row("finnhub", "news", "missing", "无标题"))
        except Exception as exc:
            rows.append(_row("finnhub", "news", "missing", finnhub.public_error(exc)))
    err = next((row.note for row in reversed(rows) if row.note), "无标题")
    return snap.model_copy(update={"news": _news_meta(
        None, "finnhub", trade_date, fetched_at, err)}), rows, None


_REDDIT_TOKEN = {"value": "", "until": 0.0}
_REDDIT_SUBS = ("stocks", "wallstreetbets")


def _social(t, keys, get, trade_date: date):
    items: list[SocialItem] = []
    if t.market != "US":
        return items, [_row("reddit", "social", "unsupported", "只覆盖美股代码")]
    if not (keys.get("REDDIT_CLIENT_ID") and keys.get("REDDIT_CLIENT_SECRET") and keys.get("REDDIT_USERNAME")):
        return items, [_row("reddit", "social", "missing", "没有 Reddit 应用凭据")]
    try:
        token = _reddit_token(keys)
        headers = {
            "Authorization": f"bearer {token}",
            "User-Agent": reddit.user_agent(keys["REDDIT_USERNAME"]),
        }
        now = datetime.now(timezone.utc)
        found: list[str] = []
        for index, name in enumerate(_REDDIT_SUBS):
            if index:
                import time
                time.sleep(1.5)
            payload = get(reddit.subreddit_search(name, t.code), headers)
            found.extend(reddit.recent_titles(payload, now))
    except Exception as exc:
        return items, [_row("reddit", "social", "missing", str(exc)[:160])]
    if not found:
        return items, [_row("reddit", "social", "missing", "24 小时内这两个版没有提到这只股票")]
    items.extend(SocialItem("reddit", title) for title in found[:5])
    return items, [_row("reddit", "social", "used")]


def _reddit_token(keys: dict) -> str:
    import time
    import httpx

    now = time.time()
    if _REDDIT_TOKEN["value"] and now < _REDDIT_TOKEN["until"]:
        return _REDDIT_TOKEN["value"]
    response = httpx.post(
        "https://www.reddit.com/api/v1/access_token",
        auth=(keys["REDDIT_CLIENT_ID"], keys["REDDIT_CLIENT_SECRET"]),
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": reddit.user_agent(keys["REDDIT_USERNAME"])},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise ValueError("Reddit 无 access_token")
    _REDDIT_TOKEN["value"] = token
    _REDDIT_TOKEN["until"] = now + int(payload.get("expires_in") or 86400) - 60
    return token


def _odds_failure(exc: BaseException) -> str:
    text = str(exc)
    lowered = text.lower()
    kind = "parse_error"
    if any(token in lowered for token in ("timed out", "timeout", "refused", "connect", "unreachable", "name or service")):
        kind = "unreachable"
    return f"{kind} {text[:120]}"


def _events(t, get, fetch_macro=None):
    items: list[EventOdds] = []
    rows = []
    mapping = polymarket.load_map()
    slug = mapping.get(t.canonical)
    if not slug:
        rows.append(_row("polymarket", "events", "skipped", "没有标的到事件的映射"))
    else:
        try:
            payload = get(f"https://gamma-api.polymarket.com/events?slug={slug}")
            found = polymarket.prices(payload)
        except Exception as exc:
            rows.append(_row("polymarket", "events", "missing", str(exc)[:160]))
        else:
            if not found:
                rows.append(_row("polymarket", "events", "missing", "映射的事件没有价格"))
            else:
                items.extend(EventOdds(slug, name, price) for name, price in found)
                rows.append(_row("polymarket", "events", "used", slug))
    try:
        raw = fetch_macro() if fetch_macro else polymarket.fetch_macro_events()
        odds = polymarket.macro_odds(raw)
    except Exception as exc:
        rows.append(_row("polymarket", "macro_odds", "missing", _odds_failure(exc)))
        return items, rows
    if not odds:
        rows.append(_row("polymarket", "macro_odds", "missing", "没有宏观事件"))
        return items, rows
    items.extend(
        EventOdds(row["slug"], row["question"], row["prob_yes"]) for row in odds
    )
    rows.append(_row("polymarket", "macro_odds", "used", f"{len(odds)} 个市场"))
    return items, rows


def clear_macro_cache() -> None:
    """Compatibility shim: macro reads go to the shared source on every run."""
