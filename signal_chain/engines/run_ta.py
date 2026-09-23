"""TradingAgents 子进程入口 —— 用 vendor/TradingAgents/.venv 的 python 执行。

用法: run_ta.py <ticker_ta格式> <trade_date YYYY-MM-DD> <out_dir>
环境: TRADINGAGENTS_* 由父进程注入（provider/backend_url/模型/patch 开关）。
产物: <out_dir>/state.json（信号评级+各报告文本）、<out_dir>/report_tree/（markdown 树）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _jsonable(v, depth: int = 0):
    if depth > 8:
        return str(v)
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, dict):
        return {str(k): _jsonable(x, depth + 1) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x, depth + 1) for x in v]
    return str(v)


def main() -> int:
    ticker, trade_date, out_dir = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out_dir.mkdir(parents=True, exist_ok=True)

    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    config = DEFAULT_CONFIG.copy()
    ta = TradingAgentsGraph(debug=False, config=config)
    final_state, signal = ta.propagate(ticker, trade_date)

    report_tree = out_dir / "report_tree"
    try:
        ta.save_reports(final_state, ticker, save_path=report_tree)
    except Exception as exc:
        print(f"save_reports failed: {exc}", file=sys.stderr)

    state = {
        "ticker": ticker,
        "trade_date": trade_date,
        "rating": signal,
        "report_tree": str(report_tree),
        "sections": _jsonable(final_state),
    }
    with open(out_dir / "state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, default=str)
    print(json.dumps({"ok": True, "rating": signal, "state": str(out_dir / "state.json")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
