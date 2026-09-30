"""screener_bridge 的离线单测：只测裁剪/去重/取标的，不连 OpenD。"""

from __future__ import annotations

import pandas as pd

from signal_chain.options.screener_bridge import _frame, candidate_of, normalize


def test_seller_normalize_dedups_candidates_and_drops_nan():
    frame = pd.DataFrame([
        {"owner": "US.NKE", "option": "US.NKE261002P35500", "annualized_return": 597.7,
         "itm_probability": 47.8, "delta": float("nan")},
        {"owner": "US.NKE", "option": "US.NKE261016P35000", "annualized_return": 210.0,
         "itm_probability": 20.0, "delta": float("nan")},
        {"owner": "US.SOXL", "option": "US.SOXL261002P146000", "annualized_return": 625.6,
         "itm_probability": 49.8, "delta": float("nan")},
    ])
    rows, candidates = normalize("seller", frame, "US", limit=10)
    assert candidates == ["US.NKE", "US.SOXL"]        # 同标的不重复
    assert rows[0]["annualized_return"] == 597.7
    assert rows[0]["itm_probability"] == 47.8
    assert "delta" not in rows[0]                     # 不在 _FIELDS 里的列不返回


def test_rank_underlying_comes_from_contract_code():
    assert candidate_of("rank", {"code": "US.NVDA260930C232500"}, "US") == "US.NVDA"
    assert candidate_of("rank", {"code": "US.BRK.B261218C500000"}, "US") == "US.BRK.B"
    # 港股合约代码的根是期权根（实测 HK.POP / HK.XIC），不是正股代码，不推。
    assert candidate_of("rank", {"code": "HK.POP261029C155000"}, "HK") is None
    assert candidate_of("rating", {"security": "US.CAG"}, "US") == "US.CAG"
    assert candidate_of("rating", {"security": None}, "US") is None


def test_frame_unwraps_rank_tuple_and_limit_truncates():
    frame = pd.DataFrame([{"security": "US.A"}, {"security": "US.B"}, {"security": "US.C"}])
    assert _frame((1801, frame)).shape == (3, 1)
    rows, candidates = normalize("movers", frame, "US", limit=2)
    assert len(rows) == 2 and candidates == ["US.A", "US.B"]
    assert normalize("movers", pd.DataFrame(), "US", limit=2) == ([], [])
