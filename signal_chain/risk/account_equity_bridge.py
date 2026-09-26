"""runtime/.venv 中运行的 Futu REAL 账户权益只读桥。"""

from __future__ import annotations

import json
import logging
import math
import sys

logging.disable(logging.CRITICAL)

_OTHER_ASSET_FIELDS = (
    "cnh_assets", "jpy_assets", "sgd_assets", "aud_assets", "cad_assets", "myr_assets",
)


def _num(row, key: str) -> float:
    try:
        value = float(row.get(key))
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(value):
        return 0.0
    return value


def main() -> int:
    market = sys.argv[1].upper()
    host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 11111

    from futu import OpenSecTradeContext, RET_OK, TrdEnv, TrdMarket

    if market == "US":
        trd_market = TrdMarket.US
    elif market == "HK":
        trd_market = TrdMarket.HK
    else:
        print(f"unsupported market: {market}", file=sys.stderr)
        return 2

    ctx = OpenSecTradeContext(filter_trdmarket=trd_market, host=host, port=port)
    try:
        ret, data = ctx.accinfo_query(trd_env=TrdEnv.REAL)
        if ret != RET_OK or data is None or data.empty:
            print(f"accinfo_query failed: {data}", file=sys.stderr)
            return 3
        row = data.iloc[0]
        print(json.dumps({
            "market": market,
            "env": "REAL",
            "currency": str(row.get("currency") or ""),
            "total_assets": _num(row, "total_assets"),
            "usd_assets": _num(row, "usd_assets"),
            "hkd_assets": _num(row, "hkd_assets"),
            "other_assets": sum(_num(row, key) for key in _OTHER_ASSET_FIELDS),
        }, ensure_ascii=False))
        return 0
    finally:
        ctx.close()


if __name__ == "__main__":
    raise SystemExit(main())
