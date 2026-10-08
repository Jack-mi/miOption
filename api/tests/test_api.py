"""api 适配层测试。fixture 用仓库真实产物 runs/2026-09-30 + chains/2026-09-30。

verdict 写测试把 SELLER_DIR 指到临时副本，不碰真实 seller store。
"""

from __future__ import annotations

import json
import shutil

import pytest
from fastapi.testclient import TestClient

from api import paths, workbench
from api.main import app

client = TestClient(app)

DAY = "2026-09-30"


def test_console_aggregate_shape():
    d = client.get("/api/console/US.AAPL").json()
    assert d["hasLedger"] is True
    assert len(d["sources"]) == 18
    states = {s["state"] for s in d["sources"]}
    assert states <= {"available", "missing", "unsupported", "stale", "unknown"}
    assert "available" in states and "missing" in states
    assert set(d["signals"]) == {"trend", "research", "value"}
    for s in d["signals"].values():
        assert s["data_status"] in ("actionable", "opinion", "insufficient_data")
    assert d["ensemble"]["agreement"] == "insufficient_data"
    # 缺字段不补 0：technical 缺失时没有数值
    assert d["technical"] == {}


def test_menu_replay_legs_and_counts():
    d = client.get("/api/console/US.AAPL").json()
    menu = d["menu"]
    assert len(menu) == 31  # 台账 31 条（27 模板 + 收租 ranked 多出的 4 条）
    ledger = json.loads((paths.RUNS_DIR / f"{DAY}.json").read_text())["tickers"]["US.AAPL"]
    for got, want in zip(menu, ledger["risk"]["menu"]):
        assert got["status"] == want["status"]  # 台账是权威
        assert got["tier"] == want["tier"]
    chain = json.loads((paths.CHAINS_DIR / DAY / "US.AAPL.json").read_text())
    codes = {r["code"] for r in chain["rows"]}
    expandable = [m for m in menu if m["expandable"]]
    assert expandable, "fit 项应能展开腿"
    for m in expandable:
        for leg in m["legs"]:
            assert leg["code"] in codes


def test_menu_replay_degrades_without_chain(monkeypatch):
    monkeypatch.setattr(paths, "load_chain", lambda day, ticker: None)
    monkeypatch.setattr(workbench.paths, "load_chain", lambda day, ticker: None)
    d = client.get("/api/console/US.AAPL").json()
    assert all(not m["expandable"] for m in d["menu"])
    assert d["chain"] is None


def test_unknown_semantics_for_ticker_without_ledger():
    d = client.get("/api/console/US.COST").json()
    assert d["hasLedger"] is False
    assert d["sources"], "无台账标的也要返回字段网格"
    assert all(s["state"] == "unknown" for s in d["sources"])
    assert len(d["menu"]) == 27
    assert all(not m["expandable"] for m in d["menu"])


def test_verdict_round_trip(tmp_path, monkeypatch):
    dst = tmp_path / "seller"
    shutil.copytree(paths.SELLER_DIR, dst)
    monkeypatch.setattr(paths, "SELLER_DIR", dst)
    monkeypatch.setattr(workbench.paths, "SELLER_DIR", dst)

    card_id = "US.AAPL-2026-10-05-bull_put_spread-330-325"
    r = client.post(f"/api/cards/{card_id}/verdict", json={"verdict": "watch"})
    assert r.status_code == 200, r.text
    cards = client.get("/api/tickers/US.AAPL/cards").json()["cards"]
    card = next(c for c in cards if c["id"] == card_id)
    assert card["verdict"] == "watch"

    r = client.post(f"/api/cards/{card_id}/verdict", json={"verdict": None})
    assert r.status_code == 200, r.text
    cards = client.get("/api/tickers/US.AAPL/cards").json()["cards"]
    card = next(c for c in cards if c["id"] == card_id)
    assert card["verdict"] is None
    # 历史卡降级：tier 仅观察 + 追加理由（只改展示，不写回）
    assert card["tier"] == "仅观察"
    assert any("历史卡片" in reason for reason in card["reasons"])


def test_recompute_cases():
    def post(ov):
        return client.post("/api/recompute", json={"ticker": "US.AAPL", **ov}).json()

    d = post({"quote": 350, "sma5": 340, "flow": 100})
    assert d["trend"]["direction"] == "strong_buy" and d["trend"]["conviction"] == 1.0
    d = post({"quote": 330, "sma5": 340, "flow": None})
    assert d["trend"]["direction"] == "sell" and d["trend"]["conviction"] == -0.5
    d = post({"quote": None, "sma5": None, "flow": None})
    assert d["trend"]["direction"] == "neutral" and d["trend"]["conviction"] == 0.0
    d = post({"quote": 350, "sma5": 340, "flow": 100, "earningsGap": 5})
    assert any("财报" in n for n in d["riskNotes"])
    # AAPL 台账其余两票弃权 → 单源折扣后 0.35 < 0.4 触发 min_conviction
    d = post({"quote": 350, "sma5": 340, "flow": None})
    assert d["ensemble"]["agreement"] == "single_source"
    assert any("低于门槛" in n for n in d["riskNotes"])
    assert len(d["notRecomputed"]) == 3


def test_evidence_endpoints():
    cov = client.get("/api/evidence/coverage?tickers=US.AAPL,US.COST").json()
    assert cov["matrix"]["US.AAPL"]["quote"] == "available"
    assert cov["matrix"]["US.COST"]["quote"] == "unknown"
    runs = client.get("/api/evidence/runs/US.AAPL").json()
    assert runs["hasLedger"] is True
    assert runs["engines"], "engines 缺失时应从信号推导"
    risk = client.get("/api/evidence/risk?ticker=US.AAPL").json()
    assert risk["limits"]["min_conviction"] == 0.4
    strats = client.get("/api/strategies").json()["strategies"]
    assert len(strats) == 27
    assert all(s["blurb"] for s in strats)


def test_watchlist_iv_and_misprice_window():
    rows = client.get("/api/watchlist").json()["rows"]
    by_ticker = {r["ticker"]: r for r in rows}
    aapl = by_ticker["US.AAPL"]
    # vol_basis 已落库：iv30 / ivRank 有真实值，不再是 null
    assert aapl["iv30"] is not None and 0 < aapl["iv30"] < 2
    assert aapl["ivRank"] is not None and 0 <= aapl["ivRank"] <= 1
    # 错价窗口规则：ivRank≥0.55 且信号可用且 |conviction|≥0.3
    for r in rows:
        if r["mispriceWindow"]:
            assert r["ivRank"] >= 0.55
            assert r["usable"]
            assert abs(r["conviction"]) >= 0.3


def test_vol_basis_field_detail():
    d = client.get("/api/console/US.AAPL/field/vol_basis").json()
    rows = dict(d["rows"])
    assert rows["iv30"] != "missing"
    assert rows["points"] == 250


def test_structured_report_is_chinese_and_clean():
    d = client.get("/api/console/US.AAPL").json()
    r = d["reportStructured"]
    # 大纲六段齐全
    for section in ("一、决策动作", "二、数据状态", "三、合成结论",
                    "四、三份信号", "五、候选结构", "六、结构菜单摘要与复核"):
        assert section in r, section
    # 不把英文报错堆进简报
    for noise in ("socksio", "pip install", "ERROR.", "Traceback", "Get Real-time"):
        assert noise not in r, noise
    # 方向是中文
    for zh in ("中性", "弃权", "观望"):
        assert zh in r
    # 无台账标的：信号行写「无记录」而不是瞎编方向
    cost = client.get("/api/console/US.COST").json()["reportStructured"]
    assert cost.count("无记录") >= 3
    assert "可行动" not in cost
