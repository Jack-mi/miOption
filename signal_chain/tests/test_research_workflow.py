"""投研工作流。注入快照，不访问公网。"""

import asyncio
import json
from datetime import date, datetime, timezone

from signal_chain.data.models import Fact, MarketData
from signal_chain.decision.signals import build_signals
from signal_chain.options.underlying_fetch import build_snapshot
from signal_chain.schema.underlying import FieldMeta

D0 = date(2026, 9, 23)
NOW = datetime(2026, 9, 23, 20, 0, tzinfo=timezone.utc)


def _market(*, fundamentals=True, facts=None):
    snap = build_snapshot(
        ticker="US.AAPL", market="US", trade_date=D0, fetched_at=NOW,
        futu={
            "quote": {"last": 180.0, "session_date": D0.isoformat(), "error": None},
            "kline": {"adjusted": True, "bars": [{
                "trade_date": D0.isoformat(),
                "open": 1, "high": 2, "low": 1, "close": 1, "volume": 1,
            }], "error": None},
        },
    )
    if fundamentals:
        snap = snap.model_copy(update={"fundamentals": FieldMeta(
            status="available", source="edgar,yfinance", as_of=D0,
            fetched_at=NOW, period="FY2026",
        )})
    return MarketData(snapshot=snap, facts=facts or [], flow_net=12.0, news_text="标题")


class _Meta:
    thread_id = "thread-finance"
    usage = {"input_tokens": 3}


def test_missing_fundamentals_do_not_call_the_model():
    class Runner:
        def __init__(self):
            self.agents = []

        async def run_json(self, agent, model, prompt, response_model, output_schema=None, retries=1):
            self.agents.append(agent)
            return response_model(rating="hold", analysis="不该出现"), None

    runner = Runner()
    signals = asyncio.run(build_signals(_market(fundamentals=False), runner, "m"))
    value = next(s for s in signals if s.engine == "value")
    assert "财务未标可用" in value.texts["analysis"]
    assert "商业模式：缺失" in value.texts["analysis"]
    assert runner.agents == ["research"]


def test_no_codex_keeps_gap_packets():
    signals = asyncio.run(build_signals(_market(), None, None))
    value = next(s for s in signals if s.engine == "value")
    assert "没有 Codex" in value.texts["analysis"]
    assert "竞争：缺失" in value.texts["analysis"]
    assert "风险：缺失" in value.texts["analysis"]
    assert value.meta == {}


def test_verifier_drops_numbers_absent_from_the_slice(tmp_path):
    class Runner:
        async def run_json(self, agent, model, prompt, response_model, output_schema=None, retries=1):
            if agent == "finance":
                return response_model(rating="buy", claims=["营收 123.0", "营收 999.0"]), _Meta()
            if agent == "verify":
                return response_model(accepted=["营收 123.0", "营收 999.0", "切片里没有的句子"]), _Meta()
            return response_model(rating="buy", analysis="营收 999.0 不该留下"), _Meta()

    facts = [Fact(source="edgar", metric="revenue", period="FY2026", value=123.0)]
    signals = asyncio.run(build_signals(
        _market(facts=facts), Runner(), "m", trace_dir=tmp_path,
    ))
    value = next(s for s in signals if s.engine == "value")
    assert "123.0" in value.texts["analysis"]
    assert "999.0" not in value.texts["analysis"]
    assert "切片里没有的句子" not in value.texts["analysis"]
    assert value.direction.value == "buy"
    assert [row["thread_id"] for row in value.meta["calls"]] == ["thread-finance"] * 3
    trace = json.loads((tmp_path / "2026-09-23_US-AAPL.jsonl").read_text(encoding="utf-8"))
    assert trace["version"] == "1"
    assert trace["model"] == "m"
    assert {p["id"] for p in trace["packets"]} == {"business", "competition", "risk", "finance"}
    assert "营收 999.0" in trace["rejected_claims"]
    assert all(p["status"] == "gap" for p in trace["packets"] if p["id"] != "finance")
