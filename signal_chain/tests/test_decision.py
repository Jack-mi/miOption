"""决策层三信号。不访问公网。"""

import asyncio
from datetime import date, datetime, timezone

from signal_chain.data.models import MarketData
from signal_chain.decision.pack import render_pack
from signal_chain.decision.signals import build_signals, render_signals, to_engine_signal
from signal_chain.options.underlying_fetch import build_snapshot
from signal_chain.schema import Direction
from signal_chain.schema.underlying import FieldMeta

D0 = date(2026, 9, 23)
NOW = datetime(2026, 9, 23, 20, 0, tzinfo=timezone.utc)


def _bars():
    rows = []
    for i in range(5):
        day = date.fromordinal(D0.toordinal() - 4 + i)
        px = 100 + i
        rows.append({
            "trade_date": day.isoformat(),
            "open": px, "high": px + 1, "low": px - 1, "close": px, "volume": 10,
        })
    return rows


def _market(*, flow_net=12.0, fundamentals=False):
    snap = build_snapshot(
        ticker="US.AAPL", market="US", trade_date=D0, fetched_at=NOW,
        futu={
            "quote": {"last": 180.0, "session_date": D0.isoformat(), "error": None},
            "kline": {"adjusted": True, "bars": _bars(), "error": None},
        },
    )
    if flow_net is not None:
        snap = snap.model_copy(update={"capital_flow": FieldMeta(
            status="available", source="futu", as_of=D0, fetched_at=NOW,
        )})
    if fundamentals:
        snap = snap.model_copy(update={"fundamentals": FieldMeta(
            status="available", source="edgar,yfinance", as_of=D0,
            fetched_at=NOW, period="FY2026",
        )})
    snap = snap.model_copy(update={"news": FieldMeta(
        status="available", source="yfinance", as_of=D0, fetched_at=NOW,
    )})
    return MarketData(snapshot=snap, flow_net=flow_net, news_text="一条标题")


def test_pack_keeps_flow_and_news_and_marks_missing_roles():
    text = render_pack(_market())
    assert "净额 12.0" in text
    assert "一条标题" in text
    assert "商业模式缺失" in text
    assert "竞争缺失" in text
    assert "风险缺失" in text
    assert "宏观缺失" in text
    assert "财务缺失" in text


def test_trend_scores_only_available_faces():
    both = to_engine_signal(asyncio.run(_one("trend", _market())))
    assert both.direction == Direction.STRONG_BUY
    assert "技术面" in (both.quality_notes or "")
    assert "资金面" in both.reasoning

    price_only = to_engine_signal(asyncio.run(_one("trend", _market(flow_net=None))))
    assert price_only.direction == Direction.BUY
    assert "资金面没有净额" in price_only.data_gaps


async def _one(name, market):
    signals = await build_signals(market, None, None)
    return next(s for s in signals if s.engine == name)


def test_research_and_value_abstain_without_codex():
    signals = asyncio.run(build_signals(_market(), None, None))
    by = {b.engine: b for b in signals}
    assert by["research"].data_status == "insufficient_data"
    assert "没有 Codex" in by["research"].data_gaps[0]
    assert by["value"].data_status == "insufficient_data"
    assert "财务未标可用" in by["value"].texts["analysis"]


def test_value_roles_stay_missing_when_fundamentals_exist():
    class Runner:
        def __init__(self):
            self.prompts = []

        async def run_json(self, agent, model, prompt, response_model, output_schema=None, retries=1):
            self.prompts.append((agent, prompt))
            if agent == "finance":
                return response_model(rating="hold", claims=["营收两源一致"]), None
            if agent == "verify":
                return response_model(accepted=["营收两源一致"]), None
            return response_model(rating="hold", analysis="营收两源一致"), None

    runner = Runner()
    signals = asyncio.run(build_signals(_market(fundamentals=True), runner, "m"))
    value = next(s for s in signals if s.engine == "value")
    assert value.direction == Direction.NEUTRAL
    assert "商业模式：缺失" in value.texts["analysis"]
    assert "竞争：缺失" in value.texts["analysis"]
    assert "风险：缺失" in value.texts["analysis"]
    assert "营收两源一致" in value.texts["analysis"]
    assert [name for name, _prompt in runner.prompts] == ["finance", "verify", "integrate", "research"]
    finance_prompt = runner.prompts[0][1]
    assert "净额" not in finance_prompt
    assert "商业模式：缺失" in runner.prompts[-1][1]
    research = next(s for s in signals if s.engine == "research")
    assert research.direction == Direction.NEUTRAL
    assert research.meta["calls"][0]["agent"] == "research"


def test_render_keeps_each_signal():
    bundles = asyncio.run(build_signals(_market(), None, None))
    text = render_signals([to_engine_signal(b) for b in bundles])
    assert "### trend" in text
    assert "### research" in text
    assert "### value" in text
    assert "没有 Codex" in text
