"""把历史日线回填进 DailyStore（daily_bars.sqlite）。

直调 bridge（不传 --scan-days，argv[5] 就是 history_start）。
bridge 的 argv 错位 bug 已在本体修复（main() 先剥离 --scan-days 再取位置参数），
这里保留直调路径以便独立使用。

落库语义与 _price_and_flow 一致（completed session 封顶、前复权）。

用法：
    .venv-sc/bin/python -m api.backfill_daily_bars HK.09992 HK.03690 [US.AAPL]
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(REPO_ROOT), str(REPO_ROOT / "runtime")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def backfill(ticker: str, trade_date: date, days: int = 120) -> int:
    from signal_chain.config import RUNTIME_VENV_PY, load_settings, parse_ticker
    from signal_chain.data.daily_store import DailyStore

    t = parse_ticker(ticker)
    store = DailyStore()
    prior = store.read(t.canonical, "futu", True, trade_date)
    start = trade_date - timedelta(days=days) if not prior else (
        date.fromisoformat(max(str(b["trade_date"])[:10] for b in prior)) - timedelta(days=7))
    settings = load_settings()
    cmd = [
        str(RUNTIME_VENV_PY), "-m", "signal_chain.options.underlying_bridge",
        t.futu_format, trade_date.isoformat(),
        str(settings.chain["futu_opend_host"]), str(settings.chain["futu_opend_port"]),
        start.isoformat(),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=str(REPO_ROOT))
    payload = None
    for line in reversed(proc.stdout.splitlines()):
        if line.strip().startswith("{"):
            payload = json.loads(line)
            break
    if payload is None:
        print(f"{ticker}: 取数失败 {proc.stderr.strip()[:300]}")
        return 0
    kline = payload.get("kline") or {}
    bars = [
        b for b in kline.get("bars") or []
        if str(b.get("trade_date") or "")[:10] <= trade_date.isoformat()
    ]
    if not bars:
        print(f"{ticker}: 没有完成日线（{kline.get('error') or '空'}）")
        return 0
    n = store.save(t.canonical, "futu", True, bars, trade_date)
    print(f"{ticker}: 落库 {n} 根（{bars[0]['trade_date']} ~ {bars[-1]['trade_date']}）")
    return n


if __name__ == "__main__":
    tickers = sys.argv[1:] or ["HK.09992", "HK.03690"]
    day = date(2026, 9, 30)  # 与最新台账 as_of 对齐，不取未完成的当日 bar
    for tk in tickers:
        backfill(tk, day)
