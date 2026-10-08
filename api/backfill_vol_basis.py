"""把 IV/HV 分位快照落进本地库（runtime/data/live/vol_basis/{ticker}.json）。

数据源与 bridge._vol_basis 相同：futu get_option_underlying_his_volatility，
250 点历史序列算分位。iv_latest 是 30 日隐含波动率（百分点）。
api 只读落库文件，不实时取数；刷新靠本脚本（可挂定时任务）。

用法：
    .venv-sc/bin/python -m api.backfill_vol_basis US.AAPL HK.09992 HK.03690
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STORE_DIR = REPO_ROOT / "runtime" / "data" / "live" / "vol_basis"


def _percentile(values: list[float], value: float) -> float:
    return round(100.0 * sum(1 for v in values if v <= value) / len(values), 2)


def fetch_vol_basis(ticker: str, host: str = "127.0.0.1", port: int = 11111) -> dict | None:
    """需要带 futu 的解释器（runtime/.venv）。文件 0600，与 daily_bars 同级纪律。"""
    import futu as ft

    ctx = ft.OpenQuoteContext(host=host, port=port)
    try:
        ret, data = ctx.get_option_underlying_his_volatility(ticker)[:2]
    finally:
        ctx.close()
    if ret != 0 or data is None or getattr(data, "empty", True):
        print(f"{ticker}: 取数失败 {str(data)[:200]}")
        return None
    series = data.sort_values("time")
    ivs = [float(v) for v in series["iv"] if v == v]
    hvs = [float(v) for v in series["hv"] if v == v]
    if not ivs or not hvs:
        print(f"{ticker}: IV/HV 序列为空")
        return None
    iv_latest, hv_latest = ivs[-1], hvs[-1]
    return {
        "ticker": ticker,
        "iv30": round(iv_latest / 100.0, 4),
        "ivRank": round(_percentile(ivs, iv_latest) / 100.0, 4),
        "hv_latest": round(hv_latest / 100.0, 4),
        "iv_hv_ratio": round(iv_latest / hv_latest, 4) if hv_latest else None,
        "points": len(ivs),
        "as_of": str(series["time"].iloc[-1])[:10],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": "futu get_option_underlying_his_volatility",
    }


def save(ticker: str, payload: dict) -> Path:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    path = STORE_DIR / f"{ticker}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return path


if __name__ == "__main__":
    tickers = sys.argv[1:] or ["US.AAPL", "HK.09992", "HK.03690"]
    for tk in tickers:
        payload = fetch_vol_basis(tk)
        if payload:
            save(tk, payload)
            print(f"{tk}: iv30={payload['iv30']} ivRank={payload['ivRank']} "
                  f"({payload['points']} 点, as_of {payload['as_of']})")
