"""数据层唯一入口。上一级 available 就不再请求下一级。"""

from __future__ import annotations

import contextlib
import io
from datetime import date, datetime, timezone
from pathlib import Path

from ..config import NormTicker, Settings
from ..options.chain_fetch import fetch_chain
from ..options.underlying_fetch import (
    build_snapshot,
    probe_futu,
    probe_yahoo,
)
from ..research.berkshire import _cross_validate, attach_fundamentals, note_earnings
from ..schema.underlying import FieldMeta
from . import alphavantage, eastmoney, edgar, polymarket, reddit, stocktwits, yahoo
from .http import get_json, get_text
from .keys import load_keys
from .models import (
    EventOdds, Fact, FilingExcerpt, MacroPoint, MarketData, Ratio, SocialItem, SourceRow,
)

_MACRO: dict[str, tuple[list[MacroPoint], list[SourceRow]]] = {}
_MACRO_FUNCTIONS = ("FEDERAL_FUNDS_RATE", "CPI", "UNEMPLOYMENT")
_EFFR_URL = "https://markets.newyorkfed.org/api/rates/unsecured/effr/last/1.json"


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
        for source in ("futu", "yfinance", "alphavantage"):
            if source not in tried and source != "futu":
                continue
            if winner == source and meta.status == "available":
                rows.append(_row(source, field, "used"))
            elif source in tried and tried[source] == "skipped":
                rows.append(_row(source, field, "skipped", "上一级已可用"))
            elif source in tried:
                rows.append(_row(source, field, "missing", tried[source]))
            elif source == "futu" and meta.status != "available":
                rows.append(_row("futu", field, "missing", meta.error or meta.status))
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


def _effr(payload: dict) -> tuple[date, float] | None:
    rows = payload.get("refRates") if isinstance(payload, dict) else None
    if not rows:
        return None
    row = rows[0]
    day = str(row.get("effectiveDate") or "")[:10]
    try:
        return date.fromisoformat(day), float(row["percentRate"])
    except (TypeError, ValueError):
        return None


def load_macro(keys: dict[str, str], today: date, get=get_json, quota=None) -> tuple[list[MacroPoint], list[SourceRow]]:
    cached = _MACRO.get(today.isoformat())
    if cached is not None:
        return cached
    if not keys.get("ALPHAVANTAGE_API_KEY"):
        result = ([], [_row("alphavantage", "macro", "skipped", "没有 ALPHAVANTAGE_API_KEY")])
        _MACRO[today.isoformat()] = result
        return result
    quota = quota or (lambda: alphavantage.take_quota(today))
    points: list[MacroPoint] = []
    errors: list[str] = []
    rate: MacroPoint | None = None
    for function in _MACRO_FUNCTIONS:
        if not quota():
            errors.append(f"{function}: 当日额度用尽")
            continue
        url = (
            "https://www.alphavantage.co/query"
            f"?function={function}&interval=monthly&apikey={keys['ALPHAVANTAGE_API_KEY']}"
        )
        try:
            obs = alphavantage.latest_indicator(get(url))
        except Exception as exc:
            errors.append(f"{function}: {str(exc)[:80]}")
            continue
        if obs is None:
            errors.append(f"{function}: 无观测")
            continue
        point = MacroPoint(function, obs[0], obs[1])
        points.append(point)
        if function == "FEDERAL_FUNDS_RATE":
            rate = point
    rows: list[SourceRow] = []
    if any(point.source == "alphavantage" for point in points):
        rows.append(_row("alphavantage", "macro", "used"))
    else:
        rows.append(_row("alphavantage", "macro", "missing", "；".join(errors) or "无观测"))
    if rate is None:
        try:
            obs = _effr(get(_EFFR_URL))
        except Exception as exc:
            obs = None
            errors.append(f"EFFR: {str(exc)[:80]}")
        if obs is None:
            rows.append(_row("nyfed", "macro", "missing", next((item for item in errors if item.startswith("EFFR")), "无观测")))
        else:
            points.append(MacroPoint("FEDERAL_FUNDS_RATE", obs[0], obs[1], "nyfed"))
            rows.append(_row("nyfed", "macro", "used"))
    result = (points, rows)
    _MACRO[today.isoformat()] = result
    return result


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
    yahoo_probe=probe_yahoo,
    chain_fetch=fetch_chain,
    yahoo_info=None,
    yahoo_news=None,
    get_text=get_text,
) -> MarketData:
    keys = keys if keys is not None else load_keys()
    fetched_at = datetime.now(timezone.utc)
    quota = quota or (lambda: alphavantage.take_quota(trade_date))
    tried: dict[str, str] = {}

    futu, futu_error = futu_probe(t, trade_date, settings)
    tried["futu"] = futu_error or "ok"
    yahoo, yahoo_error = None, None
    from ..options.underlying_fetch import _futu_field_fresh
    fresh = _futu_field_fresh(futu, trade_date, "quote") and _futu_field_fresh(futu, trade_date, "kline")
    if fresh:
        tried["yfinance"] = "skipped"
        tried["alphavantage"] = "skipped"
    else:
        yahoo, yahoo_error = yahoo_probe(t, trade_date)
        tried["yfinance"] = yahoo_error or "ok"
    snap = build_snapshot(
        ticker=t.canonical, market=t.market, trade_date=trade_date, fetched_at=fetched_at,
        futu=futu, futu_error=futu_error, yahoo=yahoo, yahoo_error=yahoo_error,
    )
    if (snap.quote.meta.status != "available" or snap.kline.meta.status != "available") and keys.get("ALPHAVANTAGE_API_KEY"):
        if quota():
            tried["alphavantage"] = "ok"
            url = (
                "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY"
                f"&symbol={t.ta_format}&apikey={keys['ALPHAVANTAGE_API_KEY']}"
            )
            try:
                payload = get(url)
                limited = alphavantage.note(payload) if isinstance(payload, dict) else None
                probe = None if limited else alphavantage.daily_probe(payload)
                if probe is None:
                    tried["alphavantage"] = limited or "无日线"
                else:
                    snap = build_snapshot(
                        ticker=t.canonical, market=t.market, trade_date=trade_date,
                        fetched_at=fetched_at,
                        futu=_probe_from_snapshot(snap),
                        yahoo=probe,
                        futu_error=snap.quote.meta.error,
                        yahoo_error=None,
                    )
                    if snap.quote.meta.source == "yfinance":
                        snap = snap.model_copy(update={
                            "quote": snap.quote.model_copy(update={
                                "meta": snap.quote.meta.model_copy(update={"source": "alphavantage"})
                            })
                        })
                    if snap.kline.meta.source == "yfinance":
                        snap = snap.model_copy(update={
                            "kline": snap.kline.model_copy(update={
                                "meta": snap.kline.meta.model_copy(update={"source": "alphavantage"})
                            }),
                            "technical": snap.technical.model_copy(update={
                                "meta": snap.technical.meta.model_copy(update={
                                    "source": "alphavantage" if snap.technical.meta.source == "yfinance" else snap.technical.meta.source
                                })
                            }),
                        })
            except Exception as exc:
                tried["alphavantage"] = str(exc)[:160]
        else:
            tried["alphavantage"] = "当日额度用尽"
    elif "alphavantage" not in tried:
        tried["alphavantage"] = "skipped"

    rows = _price_rows(snap, tried)
    snap, flow_rows, flow_net = _capital_flow(t, snap, futu, trade_date, fetched_at, get)
    rows.extend(flow_rows)
    snap, fact_rows, facts, ratios = _fundamentals(
        t, snap, trade_date, fetched_at, keys, get, quota, yahoo_info,
    )
    rows.extend(fact_rows)
    snap, earn_rows, excerpts = _earnings(
        t, snap, trade_date, fetched_at, keys, get, yahoo_info, get_text,
    )
    rows.extend(earn_rows)
    snap, news_rows, news_text = _news(t, snap, trade_date, fetched_at, keys, get, quota, yahoo_news)
    rows.extend(news_rows)

    social, social_rows = _social(t, keys, get, trade_date)
    rows.extend(social_rows)
    events, event_row = _events(t, get)
    rows.append(event_row)
    macro, macro_rows = load_macro(keys, trade_date, get, quota)
    rows.extend(macro_rows)

    chain = None
    chain_error = None
    if include_chain:
        try:
            chain = chain_fetch(t, settings)
            if chain.source == "futu":
                rows.append(_row("futu", "chain", "used"))
                rows.append(_row("yfinance", "chain", "skipped", "上一级已可用"))
            else:
                rows.append(_row("futu", "chain", "missing", chain.notes or "已降级"))
                rows.append(_row("yfinance", "chain", "used"))
        except Exception as exc:
            chain_error = str(exc)[:300]
            rows.append(_row("futu", "chain", "missing", chain_error))
            if t.market != "US":
                rows.append(_row("yfinance", "chain", "unsupported", "只兜美股"))
            else:
                rows.append(_row("yfinance", "chain", "missing", chain_error))
    return MarketData(
        snap, chain, chain_error, macro, social, events, facts, rows,
        flow_net if snap.capital_flow.status == "available" else None,
        news_text if snap.news.status == "available" else None,
        ratios,
        excerpts,
    )


def _capital_flow(t, snap, futu, trade_date, fetched_at, get):
    raw = (futu or {}).get("capital_flow") if futu else None
    meta = _flow_meta(raw, "futu", fetched_at)
    rows = []
    if meta.status == "available":
        rows.append(_row("futu", "capital_flow", "used"))
        rows.append(_row("eastmoney", "capital_flow", "skipped", "上一级已可用"))
        return snap.model_copy(update={"capital_flow": meta}), rows, float(raw["net"])
    if t.market != "HK":
        rows.append(_row("futu", "capital_flow", "missing", meta.error or ""))
        rows.append(_row("eastmoney", "capital_flow", "unsupported", "只兜港股"))
        return snap.model_copy(update={"capital_flow": _meta(
            "unsupported", None, None, fetched_at, "美股资金流没有兜底")}), rows, None
    url = (
        "https://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
        f"?lmt=1&klt=101&secid={eastmoney.hk_secid(t.code)}"
        "&fields1=f1,f2,f3,f7&fields2=f51,f52"
    )
    try:
        parsed = eastmoney.net_inflow(get(url))
    except Exception as exc:
        parsed = None
        err = str(exc)[:160]
    else:
        err = None
    if parsed is None:
        rows.append(_row("futu", "capital_flow", "missing", meta.error or ""))
        rows.append(_row("eastmoney", "capital_flow", "missing", err or "无法确认净流入"))
        return snap.model_copy(update={"capital_flow": _meta(
            "missing", "eastmoney", None, fetched_at, err or "无法确认净流入")}), rows, None
    day, value = parsed
    rows.append(_row("futu", "capital_flow", "missing", meta.error or ""))
    rows.append(_row("eastmoney", "capital_flow", "used"))
    return snap.model_copy(update={"capital_flow": _meta(
        "available", "eastmoney", date.fromisoformat(day), fetched_at)}), rows, value


def _consistent(metric: str, values: dict[str, float]) -> bool:
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return bool(_cross_validate(metric, values)["all_consistent"])
    except Exception:
        return False


def _ratio_candidates(t, facts_payload, info: dict) -> dict[str, dict[str, tuple[float, str]]]:
    found: dict[str, dict[str, tuple[float, str]]] = {}

    def put(metric: str, source: str, value: float | None, period: str) -> None:
        if value is None:
            return
        found.setdefault(metric, {})[source] = (value, period)

    if t.market == "US" and facts_payload:
        for metric, (value, period) in edgar.derived_ratios(facts_payload).items():
            put(metric, "edgar", value, period)
    put("roe", "yfinance", yahoo.named_float(info, "returnOnEquity"), "TTM")
    put("free_cash_flow", "yfinance", yahoo.named_float(info, "freeCashflow"), "TTM")
    put("interest_coverage", "yfinance", yahoo.named_float(info, "interestCoverage"), "TTM")
    return found


def _accept_ratios(candidates: dict[str, dict[str, tuple[float, str]]]):
    prefer = ("edgar", "yfinance", "eastmoney", "alphavantage")
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


def _filing_excerpts(cik: str, submissions: dict, read_text, contact: str) -> list[FilingExcerpt]:
    out: list[FilingExcerpt] = []
    headers = edgar.user_agent(contact)
    annual = edgar.latest_primary(submissions, {"10-K", "20-F"})
    if annual:
        try:
            html = read_text(edgar.archive_url(cik, annual["accession"], annual["document"]), headers)
            filed = date.fromisoformat(annual["filed"])
            for section, text in edgar.excerpts_from_10k(html).items():
                out.append(FilingExcerpt(section, text, "edgar", filed))
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


def _fundamentals(t, snap, trade_date, fetched_at, keys, get, quota, yahoo_info):
    facts: list[Fact] = []
    values: dict[str, float] = {}
    period = f"FY{trade_date.year}"
    rows: list[SourceRow] = []
    contact = keys.get("EDGAR_CONTACT", "")
    facts_payload = None
    info_box: dict = {}

    def info_for() -> dict:
        if "value" not in info_box:
            raw = yahoo_info(t) if yahoo_info else _live_yahoo_info(t)
            info_box["value"] = raw or {}
        return info_box["value"]
    if t.market == "US":
        symbol = t.code
        try:
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
            value, period, end = found
            values["edgar"] = value
            facts.append(Fact("edgar", "revenue", period, value))
            rows.append(_row("edgar", "fundamentals", "used", end))
        if len(values) >= 2:
            rows.append(_row("alphavantage", "fundamentals", "skipped", "上一级已凑齐两源"))
        elif not keys.get("ALPHAVANTAGE_API_KEY"):
            rows.append(_row("alphavantage", "fundamentals", "skipped", "没有 ALPHAVANTAGE_API_KEY"))
        elif not quota():
            rows.append(_row("alphavantage", "fundamentals", "missing", "当日额度用尽"))
        else:
            try:
                overview = get(
                    "https://www.alphavantage.co/query?function=OVERVIEW"
                    f"&symbol={symbol}&apikey={keys['ALPHAVANTAGE_API_KEY']}"
                )
                revenue = alphavantage.revenue_ttm(overview)
                if revenue is None:
                    raise ValueError(alphavantage.note(overview) or "无 RevenueTTM")
                values["alphavantage"] = revenue
                facts.append(Fact("alphavantage", "revenue", period, revenue))
                rows.append(_row("alphavantage", "fundamentals", "used"))
            except Exception as exc:
                rows.append(_row("alphavantage", "fundamentals", "missing", str(exc)[:160]))
        if len(values) < 2:
            revenue = yahoo.revenue_from_info(info_for())
            if revenue is None:
                rows.append(_row("yfinance", "fundamentals", "missing", "无 totalRevenue"))
            else:
                values["yfinance"] = revenue
                facts.append(Fact("yfinance", "revenue", period, revenue))
                rows.append(_row("yfinance", "fundamentals", "used"))
        else:
            rows.append(_row("yfinance", "fundamentals", "skipped", "上一级已凑齐两源"))
        rows.append(_row("eastmoney", "fundamentals", "unsupported", "美股不走东财"))
    else:
        rows.append(_row("edgar", "fundamentals", "unsupported", "只覆盖美股"))
        revenue = yahoo.revenue_from_info(info_for())
        if revenue is None:
            rows.append(_row("yfinance", "fundamentals", "missing", "无 totalRevenue"))
        else:
            values["yfinance"] = revenue
            facts.append(Fact("yfinance", "revenue", period, revenue))
            rows.append(_row("yfinance", "fundamentals", "used"))
        if len(values) < 2:
            url = (
                "https://datacenter.eastmoney.com/securities/api/data/v1/get"
                "?reportName=RPT_HKF10_FN_MAININDICATOR&columns=OPERATE_INCOME,REPORT_DATE"
                f"&filter=(SECUCODE=%22{t.code.zfill(5)}.HK%22)&pageSize=1"
            )
            try:
                parsed = eastmoney.revenue(get(url))
            except Exception as exc:
                parsed = None
                rows.append(_row("eastmoney", "fundamentals", "missing", str(exc)[:160]))
            if parsed:
                value, period = parsed
                values["eastmoney"] = value
                facts.append(Fact("eastmoney", "revenue", period, value))
                rows.append(_row("eastmoney", "fundamentals", "used"))
        else:
            rows.append(_row("eastmoney", "fundamentals", "skipped", "上一级已凑齐两源"))
    ratio_rows, ratio_facts, ratios = _accept_ratios(_ratio_candidates(t, facts_payload, info_for()))
    rows.extend(ratio_rows)
    facts.extend(ratio_facts)
    try:
        snap = attach_fundamentals(
            snap, metric="revenue", period=period, values=values,
            as_of=trade_date, fetched_at=fetched_at,
        )
    except Exception as exc:
        snap = snap.model_copy(update={"fundamentals": _meta(
            "missing", None, trade_date, fetched_at, str(exc)[:160])})
    return snap, rows, facts, ratios


def _live_yahoo_info(t: NormTicker) -> dict:
    try:
        import yfinance as yf
        return dict(yf.Ticker(t.ta_format).info or {})
    except Exception:
        return {}


def _yahoo_earnings_date(info: dict) -> date | None:
    raw = str((info or {}).get("earningsDate") or "")[:10]
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _earnings(t, snap, trade_date, fetched_at, keys, get, yahoo_info, read_text):
    rows = []
    excerpts: list[FilingExcerpt] = []
    contact = keys.get("EDGAR_CONTACT", "")
    if t.market == "US":
        try:
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
    else:
        rows.append(_row("edgar", "earnings", "unsupported", "港股财报日不走 EDGAR"))
    info = yahoo_info(t) if yahoo_info else _live_yahoo_info(t)
    found = _yahoo_earnings_date(info)
    if found is None:
        return snap, rows + [_row("yfinance", "earnings", "missing", "无带出处的披露日")], excerpts
    snap = note_earnings(snap, found, source="yfinance")
    return snap, rows + [_row("yfinance", "earnings", "used", found.isoformat())], excerpts


def _news(t, snap, trade_date, fetched_at, keys, get, quota, yahoo_news):
    text = None
    rows = []
    if keys.get("ALPHAVANTAGE_API_KEY") and quota():
        try:
            payload = get(
                "https://www.alphavantage.co/query?function=NEWS_SENTIMENT"
                f"&tickers={t.ta_format}&apikey={keys['ALPHAVANTAGE_API_KEY']}&limit=3"
            )
            limited = alphavantage.note(payload) if isinstance(payload, dict) else None
            text = None if limited else alphavantage.headlines(payload)
            if text:
                rows.append(_row("alphavantage", "news", "used"))
                rows.append(_row("yfinance", "news", "skipped", "上一级已可用"))
                return snap.model_copy(update={"news": _news_meta(text, "alphavantage", trade_date, fetched_at, None)}), rows, text
            rows.append(_row("alphavantage", "news", "missing", limited or "无标题"))
        except Exception as exc:
            rows.append(_row("alphavantage", "news", "missing", str(exc)[:160]))
    else:
        why = "没有 ALPHAVANTAGE_API_KEY" if not keys.get("ALPHAVANTAGE_API_KEY") else "当日额度用尽"
        rows.append(_row("alphavantage", "news", "skipped", why))
    items = yahoo_news(t) if yahoo_news else _live_yahoo_news(t)
    text = yahoo.headlines(items or [])
    rows.append(_row("yfinance", "news", "used" if text else "missing", "" if text else "无标题"))
    return snap.model_copy(update={"news": _news_meta(
        text, "yfinance", trade_date, fetched_at, None if text else "无标题")}), rows, text


def _live_yahoo_news(t: NormTicker) -> list:
    try:
        import yfinance as yf
        return list(yf.Ticker(t.ta_format).news or [])
    except Exception:
        return []


def _social(t, keys, get, trade_date: date):
    items: list[SocialItem] = []
    rows = []
    symbol = t.code
    if t.market != "US":
        return items, [
            _row("reddit", "social", "unsupported", "只覆盖美股代码"),
            _row("stocktwits", "social", "unsupported", "只覆盖美股代码"),
        ]
    if keys.get("REDDIT_CLIENT_ID") and keys.get("REDDIT_CLIENT_SECRET"):
        try:
            token = _reddit_token(keys, get)
            payload = get(
                f"https://oauth.reddit.com/search?q={symbol}&limit=3&sort=new&restrict_sr=0",
                {"Authorization": f"bearer {token}", "User-Agent": "mioption-data"},
            )
            found = reddit.titles(payload)
        except Exception as exc:
            found = []
            rows.append(_row("reddit", "social", "missing", str(exc)[:160]))
        else:
            if found:
                items.extend(SocialItem("reddit", title) for title in found)
                rows.append(_row("reddit", "social", "used"))
            else:
                rows.append(_row("reddit", "social", "missing", "无帖子"))
    else:
        rows.append(_row("reddit", "social", "skipped", "没有 Reddit 应用凭据"))
        try:
            payload = get(
                "https://arctic-shift.photon-reddit.com/api/posts/search"
                f"?subreddit=stocks&query={symbol}&limit=3&sort=desc"
            )
            titles, state = reddit.archive_posts(payload, trade_date)
        except Exception as exc:
            rows.append(_row("arctic-shift", "social", "missing", str(exc)[:160]))
        else:
            if state == "used":
                items.extend(SocialItem("arctic-shift", title) for title in titles)
                rows.append(_row("arctic-shift", "social", "used"))
            elif state == "stale":
                rows.append(_row("arctic-shift", "social", "stale", "帖子超过 14 天"))
            else:
                rows.append(_row("arctic-shift", "social", "missing", "无帖子"))
    try:
        stocktwits.wait_turn()
        found = stocktwits.titles(get(f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"))
    except Exception as exc:
        return items, rows + [_row("stocktwits", "social", "missing", str(exc)[:160])]
    if not found:
        return items, rows + [_row("stocktwits", "social", "missing", "无讨论")]
    items.extend(SocialItem("stocktwits", title) for title in found)
    return items, rows + [_row("stocktwits", "social", "used")]


def _reddit_token(keys: dict, get) -> str:
    import httpx

    response = httpx.post(
        "https://www.reddit.com/api/v1/access_token",
        auth=(keys["REDDIT_CLIENT_ID"], keys["REDDIT_CLIENT_SECRET"]),
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": "mioption-data"},
        timeout=20,
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise ValueError("Reddit 无 access_token")
    return token


def _events(t, get):
    mapping = polymarket.load_map()
    slug = mapping.get(t.canonical)
    if not slug:
        return [], _row("polymarket", "events", "skipped", "没有标的到事件的映射")
    try:
        payload = get(f"https://gamma-api.polymarket.com/events?slug={slug}")
        found = polymarket.prices(payload)
    except Exception as exc:
        return [], _row("polymarket", "events", "missing", str(exc)[:160])
    if not found:
        return [], _row("polymarket", "events", "missing", "映射的事件没有价格")
    return [EventOdds(slug, name, price) for name, price in found], _row("polymarket", "events", "used", slug)


def clear_macro_cache() -> None:
    _MACRO.clear()
