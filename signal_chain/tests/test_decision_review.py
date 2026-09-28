"""研究决策和 review。用假快照，不访问公网。"""

import asyncio
from types import SimpleNamespace

from signal_chain.agents.decision import run as run_decision
from signal_chain.agents.review import findings_for, run as run_review
from signal_chain.data.models import SourceRow
from signal_chain.tests.test_context import D0, _market

_SETTINGS = SimpleNamespace(
    models={"synthesis": "m"},
    synthesis={"aligned_boost": 1.2, "single_source_discount": 0.7, "max_asof_gap_days": 1},
    risk={
        "auto_account_equity": False,
        "earnings_blackout_days": 10,
        "min_open_interest": 100,
        "max_spread_pct": 0.1,
        "max_position_risk_pct": 0.05,
    },
)


def test_decision_refuses_without_a_snapshot():
    report = asyncio.run(run_decision(None, None, _SETTINGS, D0))
    assert report.ok is False
    assert report.error == "没有快照"


def test_decision_stops_before_the_brief():
    decided = asyncio.run(run_decision(_market(), None, _SETTINGS, D0))
    assert decided.ok is True
    assert [row["engine"] for row in decided.signal_rows] == ["trend", "research", "value"]
    assert decided.action
    assert not hasattr(decided, "markdown")


def test_review_flags_a_skip_that_was_used():
    market = _market()
    market.sources.append(SourceRow("fmp", "quote", "used", "上一级已可用"))
    decided = asyncio.run(run_decision(market, None, _SETTINGS, D0))
    assert "该跳过的源却用了" in findings_for(market, decided)


def test_review_keeps_harness_findings_when_the_model_disagrees():
    market = _market()
    market.sources.append(SourceRow("fmp", "quote", "used", "上一级已可用"))
    decided = asyncio.run(run_decision(market, None, _SETTINGS, D0))

    class Runner:
        async def run_json(self, agent, model, prompt, response_model, output_schema=None, retries=1):
            assert agent == "review"
            return response_model(verdict="pass", findings=[]), None

    report = asyncio.run(run_review(market, decided, Runner(), "m"))
    assert "该跳过的源却用了" in report.findings
