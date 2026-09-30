"""富途 OpenD 大盘筛选桥（第二条 path）—— 全市场筛出候选标的，喂给单股研究链路。

用法（用 runtime/.venv 的 python 执行，futu-api 只装在那里）:
  runtime/.venv/bin/python -m signal_chain.options.screener_bridge seller   [US|HK] [N]
  runtime/.venv/bin/python -m signal_chain.options.screener_bridge earnings [US|HK] [N]
  runtime/.venv/bin/python -m signal_chain.options.screener_bridge rank     [US|HK] [N]
  runtime/.venv/bin/python -m signal_chain.options.screener_bridge rating   [N]
  runtime/.venv/bin/python -m signal_chain.options.screener_bridge movers   [US|HK] [N]
  runtime/.venv/bin/python -m signal_chain.options.screener_bridge hot      [US|HK] [N]

输出: stdout 单行 JSON（screen / market / as_of / count / candidates / rows / error）。
`candidates` 是筛出的标的池，可直接喂给 `--tickers`。
只读：不调用交易接口。每次调用各接口只发一次请求，各自限频 60 次/30 秒（卖方专区同）。
"""

from __future__ import annotations

import json
import logging
import math
import re
import sys
from datetime import datetime, timezone

logging.disable(logging.CRITICAL)

# 每个 screen 只取这些列，多余的（希腊值、盘口等）留给单股链路按需再查。
_FIELDS = {
    "seller": ["owner", "option", "option_type", "strike_price", "strike_time", "left_days",
               "option_price", "stock_price", "premium", "otm_degree", "iv",
               "interval_return", "annualized_return", "itm_probability"],
    "earnings": ["owner", "name", "price", "change_ratio", "iv", "iv_rank", "iv_percentile",
                 "open_interest", "earnings_time", "earnings_quarter", "expected_move_ratio"],
    "rank": ["code", "name", "option_type", "volume", "open_interest", "iv", "option_price",
             "change_ratio", "delta", "trading_date"],
    "rating": ["security", "name", "change_type", "institution_name", "rating", "last_rating",
               "target_price", "last_target_price", "recommendation_date"],
    "movers": ["security", "name", "cur_price", "change_ratio", "turnover", "volume",
               "volume_ratio", "market_cap", "pe_ttm"],
    "hot": ["security", "name", "trade_heat", "search_heat", "news_heat", "average_heat",
            "news_title", "news_url"],
}
# 哪些列直接就是标的池。rank 不在里面：它返回的是合约，标的需要另推（见下）。
_TICKER_FIELD = {"seller": "owner", "earnings": "owner", "rating": "security",
                 "movers": "security", "hot": "security"}
# 合约代码形如 US.NVDA260930C232500，去掉日期+方向+行权价就是标的。
_CONTRACT_ROOT = re.compile(r"^([A-Za-z][A-Za-z.]*?)\d{6}[CP]\d+$")
_MARKET_OPT = {"US": "US_SECURITY", "HK": "HK_SECURITY"}
_MARKET = {"US": "US", "HK": "HK"}
_SCREENS = tuple(_FIELDS)


def _clean(value):
    """numpy 标量 -> python，NaN/Inf -> None。不 import numpy。"""
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (ValueError, AttributeError):
            return str(value)
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


def candidate_of(screen: str, row, market: str) -> str | None:
    """从一行里取出可喂给单股链路的标的代码。"""
    field = _TICKER_FIELD.get(screen)
    code = _clean(row.get(field)) if field else None
    if isinstance(code, str) and "." in code:
        return code
    if screen == "rank" and market == "US":
        # 只对美股推：港股合约代码的根是 HK.POP / HK.XIC 这种期权根，不是正股代码。
        raw = _clean(row.get("code"))
        if isinstance(raw, str) and "." in raw:
            m = _CONTRACT_ROOT.match(raw.split(".", 1)[1])
            if m:
                return f"{market}.{m.group(1)}"
    return None


def normalize(screen: str, frame, market: str, limit: int) -> tuple[list[dict], list[str]]:
    """把接口返回的 DataFrame 裁成 rows + 去重后的 candidates。纯函数，可离线测。"""
    fields = [f for f in _FIELDS[screen]]
    rows: list[dict] = []
    candidates: list[str] = []
    if frame is None or getattr(frame, "empty", True):
        return rows, candidates
    for _, row in frame.head(limit).iterrows():
        rows.append({f: _clean(row.get(f)) for f in fields if f in frame.columns})
        code = candidate_of(screen, row, market)
        if code and code not in candidates:
            candidates.append(code)
    return rows, candidates


def _frame(data):
    """排行类接口返回 (all_count, DataFrame)；其余直接是 DataFrame。"""
    if isinstance(data, tuple) and len(data) == 2 and hasattr(data[1], "empty"):
        return data[1]
    return data


def screen(name: str, market: str, limit: int, host: str, port: int) -> dict:
    import futu as ft

    out = {
        "screen": name,
        "market": market,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "source": "futu_screener",
        "count": 0,
        "candidates": [],
        "rows": [],
        "error": None,
    }
    ctx = ft.OpenQuoteContext(host=host, port=port)
    try:
        if name == "seller":
            # 港股只支持 CASH_SECURED_PUT；美股两种都行，这里按卖出看跌筛。
            ret, data = ctx.get_option_seller_screener(
                getattr(ft.OptionMarket, _MARKET_OPT[market]),
                ft.SellerType.CASH_SECURED_PUT, ft.SellerSortType.ANNUALIZED_RETURN)
        elif name == "earnings":
            ret, data = ctx.get_option_earnings_screener(
                getattr(ft.OptionMarket, _MARKET_OPT[market]), count=limit)
            if ret == ft.RET_OK and isinstance(data, dict):
                data = data.get("item_list")
        elif name == "rank":
            # 排行类返回 (ret, data, next_page, all_count)
            ret, data = ctx.get_option_rank(
                getattr(ft.OptionMarket, _MARKET_OPT[market]),
                ft.OptionRankType.VOLUME, count=limit)[:2]
            data = _frame(data)
        elif name == "rating":
            ret, data = ctx.get_rating_change(ft.Market.US, count=min(limit, 20))[:2]
        elif name == "movers":
            ret, data = ctx.get_top_movers_rank(
                getattr(ft.Market, _MARKET[market]), count=limit)
            data = _frame(data)
        elif name == "hot":
            ret, data = ctx.get_hot_list(getattr(ft.Market, _MARKET[market]), count=limit)
            data = _frame(data)
        else:
            raise ValueError(f"unknown screen: {name}")
    except ValueError:
        raise
    finally:
        ctx.close()

    if ret != ft.RET_OK:
        out["error"] = str(data)[:400]
        return out
    rows, candidates = normalize(name, data, market, limit)
    out["rows"] = rows
    out["candidates"] = candidates
    out["count"] = len(rows)
    return out


def main() -> None:
    argv = sys.argv[1:]
    if not argv or argv[0] not in _SCREENS:
        print(f"usage: -m signal_chain.options.screener_bridge {{{'|'.join(_SCREENS)}}} "
              f"[US|HK] [N]", file=sys.stderr)
        sys.exit(2)
    name = argv[0]
    market = (argv[1] if len(argv) > 1 else "US").upper()
    limit = int(argv[2]) if len(argv) > 2 else 20
    host = argv[3] if len(argv) > 3 else "127.0.0.1"
    port = int(argv[4]) if len(argv) > 4 else 11111
    try:
        out = screen(name, market, limit, host, port)
    except Exception as exc:  # 连不上 OpenD 也要留 JSON，退出码非零
        out = {"screen": name, "market": market,
               "as_of": datetime.now(timezone.utc).isoformat(), "source": "futu_screener",
               "count": 0, "candidates": [], "rows": [],
               "error": f"{type(exc).__name__}: {exc}"[:400]}
        print(json.dumps(out, ensure_ascii=False))
        print(out["error"], file=sys.stderr)
        sys.exit(1)
    print(json.dumps(out, ensure_ascii=False))
    if out["error"]:
        print(out["error"], file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
