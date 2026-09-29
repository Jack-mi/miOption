"""取数子 Agent。DeepSeek 会话的唯一工具是 harness 已执行的 load。"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, field
from datetime import date

from pydantic import BaseModel

from ..config import load_settings, parse_ticker
from ..data.context import _NAMES, card, slice as render_slice
from ..data.layer import load as load_market
from ..data.models import MarketData
from . import session

AGENT = "data"


class DataNote(BaseModel):
    tool: str
    note: str = ""


@dataclass
class DataReport:
    agent: str
    ticker: str
    text: str
    sources: list[dict]
    market: MarketData | None
    ok: bool = True
    calls: list[dict] = field(default_factory=list)


def render(market: MarketData) -> str:
    return "\n\n".join([card(market), *(render_slice(market, name) for name in _NAMES)])


def run(
    ticker: str,
    trade_date: date,
    settings=None,
    *,
    load_fn=None,
    include_chain: bool = True,
) -> DataReport:
    """harness 执行 load。非美股在发请求前返回。同一标的和交易日命中缓存。"""
    settings = settings if settings is not None else load_settings()
    parsed = parse_ticker(ticker) if isinstance(ticker, str) else ticker
    if parsed.market != "US":
        return DataReport(AGENT, parsed.canonical, "只覆盖美股", [], None, ok=False)
    cached = session.fresh_market(parsed.canonical, trade_date)
    if cached is None:
        cached = (load_fn or load_market)(
            parsed, trade_date, settings, include_chain=include_chain,
        )
        session.put_market(parsed.canonical, trade_date, cached)
    sources = [
        {"id": row.id, "field": row.field, "state": row.state, "note": row.note}
        for row in cached.sources
    ]
    return DataReport(AGENT, cached.snapshot.ticker, render(cached), sources, cached, ok=True)


async def collect(
    ticker: str,
    trade_date: date,
    settings=None,
    runner=None,
    model: str | None = None,
    question: str = "",
    *,
    load_fn=None,
    include_chain: bool = True,
) -> DataReport:
    report = run(
        ticker, trade_date, settings, load_fn=load_fn, include_chain=include_chain,
    )
    if not report.ok or runner is None or not model:
        return report
    prompt = (
        "你是取数子 Agent。唯一工具是 load，harness 已经执行完，结果在下面。"
        "不要改取数顺序，不要新造数据源，不要评涨跌。"
        "tool 只能填 load。\n\n"
        f"问句：{question or '全部数据'}\n\n{report.text}"
    )
    try:
        note, meta = await runner.run_json(
            AGENT, model, prompt, DataNote,
            output_schema={
                "type": "object",
                "properties": {"tool": {"type": "string"}, "note": {"type": "string"}},
                "required": ["tool"],
            },
        )
    except Exception as exc:
        report.calls.append({"agent": AGENT, "thread_id": None, "usage": None, "error": str(exc)[:160]})
        return report
    if note.tool != "load":
        report.text += "\n取数工具不是 load，结果仍以 harness 为准"
    usage = getattr(meta, "usage", None) if meta is not None else None
    thread_id = getattr(meta, "thread_id", None) if meta is not None else None
    report.calls.append({"agent": AGENT, "thread_id": thread_id, "usage": usage})
    return report


def run_public(ticker: str, trade_date: date | None = None, question: str = "") -> dict:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    report = asyncio.run(collect(ticker, trade_date or datetime.now(ZoneInfo("America/New_York")).date(), question=question))
    return {
        "ok": report.ok,
        "agent": report.agent,
        "ticker": report.ticker,
        "text": report.text,
        "sources": report.sources,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="取数子 Agent")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--date", default=None)
    args = parser.parse_args()
    day = date.fromisoformat(args.date) if args.date else date.today()
    report = run(args.ticker, day)
    print(report.text)


if __name__ == "__main__":
    main()
