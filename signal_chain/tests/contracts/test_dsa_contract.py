"""DSA 适配器契约测试（合成 fixture，M0 后替换为真实报告）。"""

from datetime import date
from pathlib import Path

from signal_chain.adapters import DsaAdapter
from signal_chain.config import parse_ticker
from signal_chain.schema import Direction

SAMPLE = """# 决策仪表盘 2026-09-23

## 00700 腾讯控股

评分: 78 | 操作: 买入

舆情偏积极，资金面 5 日净流入转正。风险：游戏监管。

## AAPL 苹果

评分: 45 | 操作: 观望

缺乏催化剂。
"""


def test_dsa_section_and_mapping(tmp_path: Path):
    report = tmp_path / "report_20260923.md"
    report.write_text(SAMPLE, encoding="utf-8")
    t = parse_ticker("HK.00700")
    bundle = DsaAdapter().load(report, t, date(2026, 9, 23))
    assert bundle.valid
    assert bundle.direction == Direction.BUY
    assert abs(bundle.conviction - (78 - 50) / 50) < 1e-6
    assert "腾讯" in bundle.texts["report_section"]


def test_dsa_strong_buy_threshold(tmp_path: Path):
    report = tmp_path / "r.md"
    report.write_text("## AAPL\n\n评分: 90 | 操作: 买入\n\n强。", encoding="utf-8")
    bundle = DsaAdapter().load(report, parse_ticker("US.AAPL"), date(2026, 9, 23))
    assert bundle.direction == Direction.STRONG_BUY
