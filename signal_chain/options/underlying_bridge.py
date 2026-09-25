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
        ret, snap = quote_ctx.get_market_snapshot([symbol])
        if ret != ft.RET_OK or snap is None or snap.empty:
            quote["error"] = f"snapshot 失败: {snap}"[:400]
        else:
            row = snap.iloc[0]
            session = _session_date(row.get("update_time"))
            last = _num(row.get("last_price"))
            if last is None or session is None:
                quote["error"] = "snapshot 无 last_price 或 update_time，不能确认交易日"
            else:
                quote["last"] = last
                quote["session_date"] = session

        start = (trade_date - timedelta(days=120)).isoformat()
        bars, k_error = _history(quote_ctx, symbol, start, trade_date.isoformat())
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
