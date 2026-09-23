"""TA 适配器契约测试（合成 fixture，M0 后替换为真实 state.json）。"""

import json
from datetime import date
from pathlib import Path

from signal_chain.adapters import TaAdapter
from signal_chain.config import parse_ticker
from signal_chain.schema import Direction


def _write_state(tmp_path: Path, rating: str) -> Path:
    state = {
        "ticker": "AAPL",
        "trade_date": "2026-09-23",
        "rating": rating,
        "report_tree": str(tmp_path / "tree"),
        "sections": {"final_trade_decision": "BUY: 基本面强劲", "market_report": "RSI 健康"},
    }
    p = tmp_path / "state.json"
    p.write_text(json.dumps(state), encoding="utf-8")
    return p


def test_ta_rating_map(tmp_path: Path):
    t = parse_ticker("US.AAPL")
    bundle = TaAdapter().load(_write_state(tmp_path, "Overweight"), t, date(2026, 9, 23))
    assert bundle.direction == Direction.BUY
    assert bundle.conviction == 0.5
    assert "final_trade_decision" in bundle.texts


def test_ta_review_invalid(tmp_path: Path):
    t = parse_ticker("US.AAPL")
    bundle = TaAdapter().load(_write_state(tmp_path, "REVIEW"), t, date(2026, 9, 23))
    assert not bundle.valid
