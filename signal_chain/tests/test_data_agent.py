"""取数子 Agent。用假 load，不访问公网。"""

import asyncio

from signal_chain.agents import session
from signal_chain.agents.data import collect, run
from signal_chain.data.models import SourceRow
from signal_chain.tests.test_context import D0, _market


def test_data_agent_returns_slices_and_does_not_score():
    session.clear()
    market = _market()
    market.sources.append(SourceRow("fmp", "quote", "skipped", "上一级已可用"))

    def fake_load(parsed, trade_date, settings, *, include_chain=True):
        assert parsed.canonical == "US.AAPL"
        assert trade_date == D0
        assert include_chain is True
        return market

    report = run("AAPL", D0, object(), load_fn=fake_load)
    assert report.ok is True
    assert report.agent == "data"
    assert "上一级已可用" in report.text
    assert "109.0" in report.text
    assert "同向偏多" not in report.text


def test_cached_snapshot_is_not_loaded_again():
    session.clear()
    market = _market()
    calls = {"n": 0}

    def fake_load(*_args, **_kwargs):
        calls["n"] += 1
        return market

    run("AAPL", D0, object(), load_fn=fake_load)
    run("US.AAPL", D0, object(), load_fn=fake_load)
    assert calls["n"] == 1


def test_data_agent_session_names_only_load():
    session.clear()
    market = _market()

    class Runner:
        def __init__(self):
            self.prompts = []

        async def run_json(self, agent, model, prompt, response_model, output_schema=None, retries=1):
            self.prompts.append((agent, prompt))
            return response_model(tool="load", note="已取数"), None

    runner = Runner()
    report = asyncio.run(collect(
        "AAPL", D0, object(), runner, "m", "全部数据",
        load_fn=lambda *a, **k: market,
    ))
    assert report.calls[0]["agent"] == "data"
    assert "唯一工具是 load" in runner.prompts[0][1]


def test_data_agent_refuses_non_us_without_a_fetch():
    session.clear()
    def fake_load(*_args, **_kwargs):
        raise AssertionError("非美股不应取数")

    report = run("HK.00700", D0, object(), load_fn=fake_load)
    assert report.ok is False
    assert report.text == "只覆盖美股"
    assert report.agent == "data"
