"""Futu OpenD 只读报价与日线探测。用 runtime/.venv 的 python 执行（futu-api 只装在那里）。

用法: runtime/.venv/bin/python -m signal_chain.options.underlying_bridge US.AAPL 2026-09-23
输出: stdout 单行 JSON。连接失败时退出码非零，JSON 仍带 error。不调用交易接口。
"""

from __future__ import annotations

import json
import logging
import math
import sys
from datetime import date, datetime, timedelta, timezone

logging.disable(logging.CRITICAL)

_TZ = {"US": "America/New_York", "HK": "Asia/Hong_Kong"}
_NEWS_KEYWORDS = {"HK.09992": "泡泡瑪特", "HK.03690": "美團"}


def _num(v):
    try:
        f = float(v)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


def _session_date(value) -> str | None:
    text = str(value or "").strip()
    if len(text) < 10:
        return None
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        return None


def _bars_from_frame(data) -> list[dict]:
    bars = []
    if data is None or getattr(data, "empty", True):
        return bars
    for _, row in data.iterrows():
        session = _session_date(row.get("time_key"))
        close = _num(row.get("close"))
        if session is None or close is None:
            continue
        bars.append({
            "trade_date": session,
            "open": _num(row.get("open")),
            "high": _num(row.get("high")),
            "low": _num(row.get("low")),
            "close": close,
            "volume": _num(row.get("volume")),
        })
    return bars


def _history(quote_ctx, symbol: str, start: str, end: str):
    import futu as ft

    bars: list[dict] = []
    page_key = None
    last_error = None
    for _ in range(8):
        kwargs = dict(ktype=ft.KLType.K_DAY, autype=ft.AuType.QFQ, max_count=100)
        if page_key:
            ret, data, page_key = quote_ctx.request_history_kline(
                symbol, page_req_key=page_key, **kwargs)
        else:
            ret, data, page_key = quote_ctx.request_history_kline(
                symbol, start=start, end=end, **kwargs)
        if ret != ft.RET_OK:
            last_error = str(data)[:400]
            break
        bars.extend(_bars_from_frame(data))
        if not page_key:
            return bars, None
    if bars and last_error is None:
        return bars, None
    try:
        ret, data = quote_ctx.get_cur_kline(symbol, 90, ft.KLType.K_DAY, ft.AuType.QFQ)
    except Exception as exc:
        return [], last_error or str(exc)[:400]
    if ret != ft.RET_OK:
        joined = "；".join(x for x in (last_error, str(data)[:200]) if x)
        return [], joined or "日线请求失败"
    cur = _bars_from_frame(data)
    if not cur:
        return [], last_error or "日线为空"
    return cur, None


def _capital_flow(quote_ctx, symbol: str) -> dict:
    """只要净流入。没有 in_flow 就不把成交额写进来。"""
    try:
        ret, data = quote_ctx.get_capital_flow(symbol)
    except Exception as exc:
        return {"net": None, "as_of": None, "error": str(exc)[:200]}
    if ret != 0 or data is None or getattr(data, "empty", True):
        return {"net": None, "as_of": None, "error": str(data)[:200]}
    row = data.iloc[-1]
    net = _num(row.get("in_flow"))
    session = _session_date(row.get("capital_flow_item_time"))
    if net is None or session is None:
        return {"net": None, "as_of": None, "error": "无 in_flow，不能当成资金流"}
    return {"net": net, "as_of": session, "error": None}


def _report_items(report: dict) -> dict[str, float | None]:
    return {
        str(item.get("display_name")): _num(item.get("data"))
        for item in report.get("item_list", [])
    }


def _financials(quote_ctx, symbol: str, snapshot_row) -> dict:
    income_ret, income = quote_ctx.get_financials_statements(symbol, statement_type=1, num=4)
    metric_ret, metrics = quote_ctx.get_financials_statements(symbol, statement_type=4, num=4)
    income_reports = income.get("report_list", []) if income_ret == 0 and isinstance(income, dict) else []
    metric_reports = metrics.get("report_list", []) if metric_ret == 0 and isinstance(metrics, dict) else []
    if not income_reports:
        return {"error": "Futu 无利润表", "period": None, "as_of": None}
    latest = income_reports[0]
    same_period = next((r for r in metric_reports if r.get("period_text") == latest.get("period_text")), metric_reports[0] if metric_reports else None)
    income_items = _report_items(latest)
    metric_items = _report_items(same_period) if same_period else {}
    return {
        "period": latest.get("period_text"),
        "as_of": latest.get("date_time_str"),
        "currency": latest.get("currency_code"),
        "auditor_report": latest.get("auditor_report") or None,
        "income": {
            "revenue": income_items.get("Total Revenue"),
            "gross_profit": income_items.get("Gross Profit"),
            "operating_profit": income_items.get("Operating Profit"),
            "net_profit": income_items.get("Net Profit"),
            "net_profit_parent": income_items.get("Net Income to Parent Company"),
            "basic_eps": income_items.get("Basic EPS"),
            "diluted_eps": income_items.get("Diluted EPS"),
        },
        "metrics": {
            "period": same_period.get("period_text") if same_period else None,
            "as_of": same_period.get("date_time_str") if same_period else None,
            "net_asset_per_share": metric_items.get("Net Assets Per Share"),
            "gross_margin": metric_items.get("Gross Profit Ratio"),
            "operating_margin": metric_items.get("Operating Profit Ratio"),
            "net_margin": metric_items.get("Net Profit Ratio"),
            "roe": metric_items.get("ROE"),
            "roa": metric_items.get("ROA"),
            "current_ratio": metric_items.get("Current Ratio"),
            "quick_ratio": metric_items.get("Quick Ratio"),
            "inventory_turnover": metric_items.get("Inventory Turnover (T)"),
        },
        "valuation": {
            "as_of": _session_date(snapshot_row.get("update_time")),
            "currency": "HKD",
            "market_cap": _num(snapshot_row.get("total_market_val")),
            "pe_ttm": _num(snapshot_row.get("pe_ttm_ratio")),
            "pb": _num(snapshot_row.get("pb_ratio")),
            "dividend_ttm": _num(snapshot_row.get("dividend_ttm")),
            "dividend_yield_ttm": _num(snapshot_row.get("dividend_ratio_ttm")),
        },
        "error": None,
    }


def _research(quote_ctx, symbol: str) -> dict:
    ret, report = quote_ctx.get_research_morningstar_report(symbol)
    if ret != 0 or not isinstance(report, dict):
        return {"sections": {}, "error": str(report)[:200]}
    sections = {
        "business": report.get("investment_thesis_content", {}).get("context"),
        "competition": report.get("economic_moat_content", {}).get("context"),
        "risk_factors": report.get("uncertainty_content", {}).get("context"),
        "governance": report.get("capital_allocation_content", {}).get("context"),
        "financial_health": report.get("financial_health_content", {}).get("context"),
    }
    return {
        "sections": {key: value for key, value in sections.items() if value},
        "as_of": report.get("analyst_report_update_time_str"),
        "source": "futu_morningstar",
        "star_rating": report.get("star_rating"),
        "fair_value": report.get("fair_value"),
        "moat": report.get("economic_moat_label"),
        "uncertainty": report.get("uncertainty_label"),
        "analyst": report.get("analyst_report_by_line"),
        "error": None,
    }


def _news(quote_ctx, name: str, today: date) -> list[dict]:
    import futu as ft

    ret, frame = quote_ctx.get_search_news(name, max_count=10, news_sub_type=ft.NewsSubType.NEWS)
    if ret != 0 or frame is None or frame.empty:
        return []
    out = []
    for _, row in frame.iterrows():
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        raw_time = str(row.get("publish_time") or "").strip()
        try:
            month, day = (int(part) for part in raw_time.split("/", 1))
            published = date(today.year, month, day)
            if (published - today).days > 30:
                published = date(today.year - 1, month, day)
        except (ValueError, TypeError):
            published = None
        out.append({
            "title": title,
            "source": str(row.get("source") or "futu_news"),
            "published": published.isoformat() if published else None,
            "url": str(row.get("url") or "") or None,
        })
    return out[:5]


def probe(symbol: str, trade_date: date, host: str, port: int) -> dict:
    import futu as ft

    market, code = symbol.split(".", 1)
    if market == "HK":
        code = code.zfill(5)
    symbol = f"{market}.{code}"
    fetched_at = datetime.now(timezone.utc).isoformat()
    quote_ctx = ft.OpenQuoteContext(host=host, port=port)
    try:
        quote = {"last": None, "session_date": None, "error": None}
        name = ""
        snapshot_row = None
        ret, snap = quote_ctx.get_market_snapshot([symbol])
        if ret != ft.RET_OK or snap is None or snap.empty:
            quote["error"] = f"snapshot 失败: {snap}"[:400]
        else:
            row = snap.iloc[0]
            snapshot_row = row
            name = str(row.get("name") or "").strip()
            raw_update = row.get("update_time")
            update_text = "" if raw_update is None else str(raw_update).strip()
            if update_text.lower() in {"nat", "nan", "none"}:
                update_text = ""
            session = _session_date(update_text)
            last = _num(row.get("last_price"))
            if last is None or session is None:
                quote["error"] = "snapshot 无 last_price 或 update_time，不能确认交易日"
            else:
                quote["last"] = last
                quote["session_date"] = session
                quote["update_time"] = update_text
                quote["observed_at"] = datetime.now(timezone.utc).isoformat()

        start = sys.argv[5] if len(sys.argv) > 5 else (trade_date - timedelta(days=120)).isoformat()
        bars, k_error = (_history(quote_ctx, symbol, start, trade_date.isoformat())
                         if start <= trade_date.isoformat() else ([], None))
        kline = {
            "adjusted": True,
            "bars": bars,
            "error": k_error,
        }
        return {
            "ok": True,
            "ticker": symbol,
            "market": market,
            "timezone": _TZ.get(market, "UTC"),
            "fetched_at": fetched_at,
            "quote": quote,
            "kline": kline,
            "capital_flow": _capital_flow(quote_ctx, symbol),
            "name": name,
            "financials": _financials(quote_ctx, symbol, snapshot_row) if snapshot_row is not None else {"error": "snapshot 缺失"},
            "research": _research(quote_ctx, symbol),
            "news": _news(quote_ctx, _NEWS_KEYWORDS.get(symbol, name), trade_date)
                     if _NEWS_KEYWORDS.get(symbol, name) else [],
            "error": None,
        }
    finally:
        quote_ctx.close()


def main() -> int:
    symbol = sys.argv[1]
    trade_date = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today()
    host = sys.argv[3] if len(sys.argv) > 3 else "127.0.0.1"
    port = int(sys.argv[4]) if len(sys.argv) > 4 else 11111
    market = symbol.split(".", 1)[0]
    try:
        payload = probe(symbol, trade_date, host, port)
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({
            "ok": False,
            "ticker": symbol,
            "market": market,
            "timezone": _TZ.get(market, "UTC"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "quote": {"last": None, "session_date": None, "error": None},
            "kline": {"adjusted": True, "bars": [], "error": None},
            "capital_flow": {"net": None, "as_of": None, "error": None},
            "error": str(exc)[:400],
        }, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
