"""runtime/.venv 中运行的 Futu REAL 账户权益只读桥。"""

from __future__ import annotations

import json
import logging
import sys

logging.disable(logging.CRITICAL)


def main() -> int:
    market = sys.argv[1].upper()
    host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 11111

    from futu import OpenSecTradeContext, RET_OK, TrdEnv, TrdMarket

    if market == "US":
        trd_market, field, currency = TrdMarket.US, "usd_assets", "USD"
    elif market == "HK":
        trd_market, field, currency = TrdMarket.HK, "hkd_assets", "HKD"
    else:
        print(f"unsupported market: {market}", file=sys.stderr)
        return 2

    ctx = OpenSecTradeContext(filter_trdmarket=trd_market, host=host, port=port)
    try:
        ret, data = ctx.accinfo_query(trd_env=TrdEnv.REAL)
        if ret != RET_OK or data is None or data.empty:
            print(f"accinfo_query failed: {data}", file=sys.stderr)
            return 3
        value = data.iloc[0].get(field)
        print(json.dumps({
            "market": market, "field": field, "currency": currency,
            "value": value, "env": "REAL",
        }, ensure_ascii=False, default=str))
        return 0
    finally:
        ctx.close()


if __name__ == "__main__":
    raise SystemExit(main())
