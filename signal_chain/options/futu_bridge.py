"""Futu OpenD 取链桥 —— 用 runtime/.venv 的 python 执行（futu-api 只装在那里）。

用法:  runtime/.venv/bin/python -m signal_chain.options.futu_bridge US.AAPL 60
输出:  stdout 单行 JSON（ChainSnapshot 兼容字典）。错误写 stderr，退出码非零。
只读：不触碰任何交易接口。
"""

from __future__ import annotations

import json
import logging
import math
import sys
import time
from datetime import date, datetime, timedelta, timezone

logging.disable(logging.CRITICAL)  # futu 库日志走 stdout，会污染 JSON 输出

# Futu OpenD 频控（2026-09-23 实测）：get_option_chain 限 10 次/30 秒。
# 链查询按 3.2s 间隔 pacing，撞限退避 31s 重试一次。
_CHAIN_MIN_INTERVAL = 3.2
_last_chain_call = 0.0


def _option_chain_paced(quote_ctx, symbol: str, exp: str):
    import futu as ft

    global _last_chain_call
    for attempt in range(2):
        gap = time.monotonic() - _last_chain_call
        if gap < _CHAIN_MIN_INTERVAL:
            time.sleep(_CHAIN_MIN_INTERVAL - gap)
        _last_chain_call = time.monotonic()
        ret, chain = quote_ctx.get_option_chain(symbol, start=exp, end=exp)
        if ret == ft.RET_OK:
            return ret, chain
        if "high frequency" in str(chain) and attempt == 0:
            print(f"chain 频控，退避 31s 重试: {symbol} {exp}", file=sys.stderr)
            time.sleep(31.0)
            _last_chain_call = time.monotonic()
            continue
        return ret, chain
    return ret, chain


def _num(v):
    try:
        f = float(v)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


def _int(v):
    f = _num(v)
    return None if f is None else int(f)


def _iv(v):
    """Futu option_implied_volatility 是百分数（23.93=23.93%），归一到小数。"""
    f = _num(v)
    if f is None or f <= 0:
        return None
    return round(f / 100.0, 6)


def _get(row, *keys):
    for k in keys:
        try:
            v = row.get(k)
        except AttributeError:
            v = None
        if v is not None:
            return v
    return None


def main() -> int:
    underlying = sys.argv[1]            # Futu 格式 US.AAPL / HK.00700
    window_days = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    host = sys.argv[3] if len(sys.argv) > 3 else "127.0.0.1"
    port = int(sys.argv[4]) if len(sys.argv) > 4 else 11111

    import futu as ft

    market, code = underlying.split(".", 1)
    if market == "HK":
        code = code.zfill(5)
    symbol = f"{market}.{code}"

    quote_ctx = ft.OpenQuoteContext(host=host, port=port)
    try:
        ret, snap = quote_ctx.get_market_snapshot([symbol])
        if ret != ft.RET_OK or snap is None or snap.empty:
            print(f"spot snapshot failed: {snap}", file=sys.stderr)
            return 2
        spot = _num(snap.iloc[0].get("last_price"))

        ret, dates = quote_ctx.get_option_expiration_date(symbol)
        if ret != ft.RET_OK:
            print(f"expiration dates failed: {dates}", file=sys.stderr)
            return 3
        today = date.today()
        horizon = today + timedelta(days=window_days)
        expiries = [
            d for d in dates["strike_time"].tolist()
            if today <= datetime.strptime(d, "%Y-%m-%d").date() <= horizon
        ]
        if not expiries:
            print("no expiries in window", file=sys.stderr)
            return 4

        rows: list[dict] = []
        for exp in expiries:
            ret, chain = _option_chain_paced(quote_ctx, symbol, exp)
            if ret != ft.RET_OK or chain is None or chain.empty:
                print(f"chain empty for {symbol} exp={exp}: ret={ret}", file=sys.stderr)
                continue
            codes = chain["code"].tolist()
            ret, snaps = quote_ctx.get_market_snapshot(codes)
            snap_map = {}
            if ret == ft.RET_OK and snaps is not None and not snaps.empty:
                for _, r in snaps.iterrows():
                    snap_map[r["code"]] = r
            for _, c in chain.iterrows():
                s = snap_map.get(c["code"])
                rows.append({
                    "code": c["code"],
                    "strike": _num(c.get("strike_price")),
                    "expiry": exp,
                    "option_type": "CALL"
                    if str(c.get("option_type")).upper().startswith("CALL")
                    else "PUT",
                    "bid": _num(_get(s, "bid_price", "Bid_price")) if s is not None else None,
                    "ask": _num(_get(s, "ask_price", "Ask_price")) if s is not None else None,
                    "last": _num(_get(s, "last_price")) if s is not None else None,
                    "iv": _iv(_get(s, "option_implied_volatility")) if s is not None else None,
                    "delta": _num(_get(s, "option_delta")) if s is not None else None,
                    "open_interest": _int(_get(s, "option_open_interest")) if s is not None else None,
                    "volume": _int(_get(s, "volume")) if s is not None else None,
                })

        out = {
            "ticker": symbol,
            "market": market,
            "as_of": today.isoformat(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "futu",
            "spot": spot,
            "rows": rows,
            "degraded": False,
            "notes": None,
        }
        print(json.dumps(out, ensure_ascii=False))
        return 0
    finally:
        quote_ctx.close()


if __name__ == "__main__":
    sys.exit(main())
