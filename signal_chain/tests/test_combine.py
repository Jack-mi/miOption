"""合成规则：aligned / partial / conflicted / single_source / as_of 错位。"""

from datetime import date, timedelta

from signal_chain.schema import Direction, EngineSignal
from signal_chain.synth.combine import combine, direction_from_conviction

D0 = date(2026, 9, 23)


def _sig(engine, direction, conviction, as_of=D0):
    return EngineSignal(
        signal_id=f"{engine}-US.AAPL-{as_of}-x",
        engine=engine, raw_report_ref="/tmp/x",
        ticker="US.AAPL", market="US", as_of=as_of,
        direction=direction, conviction=conviction,
    )


def test_three_votes_all_count():
    e = combine([
        _sig("trend", Direction.BUY, 0.5),
        _sig("research", Direction.BUY, 0.5),
        _sig("value", Direction.NEUTRAL, 0.0),
    ], as_of=D0)
    assert e.agreement == "partial"
    assert len(e.components) == 3
    assert abs(e.conviction - 0.3333) < 1e-6


def test_aligned_boost():
    e = combine([_sig("dsa", Direction.BUY, 0.5),
                 _sig("tradingagents", Direction.BUY, 1.0)], as_of=D0)
    assert e.agreement == "aligned"
    assert abs(e.conviction - min(1.0, 0.75 * 1.2)) < 1e-6
    assert e.direction == Direction.STRONG_BUY


def test_partial_with_neutral():
    e = combine([_sig("dsa", Direction.BUY, 0.6),
                 _sig("tradingagents", Direction.NEUTRAL, 0.0)], as_of=D0)
    assert e.agreement == "partial"
    assert abs(e.conviction - 0.3) < 1e-6


def test_conflicted():
    e = combine([_sig("dsa", Direction.BUY, 0.8),
                 _sig("tradingagents", Direction.SELL, -0.6)], as_of=D0)
    assert e.agreement == "conflicted"
    assert abs(e.conviction - 0.1) < 1e-6


def test_single_source_discount():
    e = combine([_sig("dsa", Direction.BUY, 1.0)], as_of=D0)
    assert e.agreement == "single_source"
    assert abs(e.conviction - 0.7) < 1e-6


def test_asof_gap_degrades_older():
    old = _sig("dsa", Direction.SELL, -0.8, as_of=D0 - timedelta(days=5))
    new = _sig("tradingagents", Direction.BUY, 1.0)
    e = combine([old, new], as_of=D0, max_asof_gap_days=1)
    degraded = [c for c in e.components if c.degraded]
    assert len(degraded) == 1 and degraded[0].engine == "dsa"
    assert e.agreement == "single_source"  # 旧信号降级后只剩 TA 有效


def test_insufficient_peer_becomes_single_source():
    weak = _sig("dsa", Direction.NEUTRAL, 0.0)
    weak = weak.model_copy(update={
        "data_status": "insufficient_data",
        "degraded": True,
        "data_gaps": ["报价 missing: 无报价"],
    })
    e = combine([weak, _sig("tradingagents", Direction.BUY, 1.0)], as_of=D0)
    assert e.agreement == "single_source"
    assert abs(e.conviction - 0.7) < 1e-6
    assert e.quality_notes and "dsa" in e.quality_notes


def test_opinion_still_votes_with_peer():
    view = _sig("dsa", Direction.NEUTRAL, 0.0).model_copy(update={
        "data_status": "opinion",
        "data_gaps": ["报告标明关键数据缺失: 行情缺失"],
    })
    e = combine([view, _sig("tradingagents", Direction.BUY, 0.5)], as_of=D0)
    assert e.agreement == "partial"
    assert e.direction == Direction.BUY
    assert "观点保留" in (e.quality_notes or "")
    assert "不是双源行情互证" not in (e.quality_notes or "")


def test_both_opinions_are_not_dual_price_confirmation():
    a = _sig("dsa", Direction.BUY, 0.4).model_copy(update={"data_status": "opinion"})
    b = _sig("tradingagents", Direction.BUY, 0.6).model_copy(update={"data_status": "opinion"})
    e = combine([a, b], as_of=D0)
    assert e.agreement == "aligned"
    assert "不是双源行情互证" in (e.quality_notes or "")


def test_both_insufficient_does_not_vote():
    def abstain(engine):
        return _sig(engine, Direction.NEUTRAL, 0.0).model_copy(update={
            "data_status": "insufficient_data",
            "data_gaps": ["日线 missing: 无日线"],
        })
    e = combine([abstain("dsa"), abstain("tradingagents")], as_of=D0)
    assert e.agreement == "insufficient_data"
    assert e.direction == Direction.NEUTRAL
    assert e.conviction == 0.0
    assert len(e.components) == 2


def test_direction_thresholds():
    assert direction_from_conviction(0.6) == Direction.STRONG_BUY
    assert direction_from_conviction(0.2) == Direction.BUY
    assert direction_from_conviction(0.0) == Direction.NEUTRAL
    assert direction_from_conviction(-0.6) == Direction.STRONG_SELL
