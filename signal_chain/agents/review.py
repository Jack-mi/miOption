"""Review 子 Agent。紧跟研究决策，只报告毛病，不取数，不改方向。"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from ..data.context import slice as render_slice
from ..research.workflow import _numbers
from ..schema import Direction
from . import session

AGENT = "review"


class ReviewNote(BaseModel):
    verdict: str = ""
    findings: list[str] = []


@dataclass
class ReviewReport:
    ok: bool
    agent: str = AGENT
    ticker: str = ""
    findings: list[str] = field(default_factory=list)
    calls: list[dict] = field(default_factory=list)
    error: str = ""


def findings_for(market, decision) -> list[str]:
    found: list[str] = []
    if market is not None:
        status = {
            "quote": market.snapshot.quote.meta.status,
            "kline": market.snapshot.kline.meta.status,
            "technical": market.snapshot.technical.meta.status,
            "capital_flow": market.snapshot.capital_flow.status,
            "fundamentals": market.snapshot.fundamentals.status,
            "news": market.snapshot.news.status,
        }
        by_field: dict[str, list] = {}
        for row in market.sources:
            if row.state == "used" and "上一级已可用" in (row.note or ""):
                found.append("该跳过的源却用了")
            by_field.setdefault(row.field, []).append(row)
        for field_name, rows in by_field.items():
            if status.get(field_name) == "available" and rows and all(
                row.state in {"missing", "skipped"} for row in rows
            ):
                found.append("失败被写成可用")
        finance = "\n".join(
            render_slice(market, name) for name in ("fundamentals", "earnings", "filing")
        )
        allowed = _numbers(finance)
        for sig in decision.signals:
            if sig.engine != "value":
                continue
            nums = _numbers("\n".join(getattr(sig, "claims", None) or []))
            if nums and not nums <= allowed:
                found.append("价值主张里的数字切片对不上")
    voting = [
        sig.direction for sig in decision.signals if sig.data_status != "insufficient_data"
    ]
    ensemble = decision.ensemble
    for sig in decision.signals:
        if (
            sig.data_status == "insufficient_data"
            and ensemble.direction == sig.direction
            and ensemble.direction != Direction.NEUTRAL
            and sig.direction not in voting
        ):
            found.append("弃权票参与了合成")
    original = {sig.engine: sig.direction for sig in decision.signals}
    for comp in ensemble.components:
        if original.get(comp.engine) != comp.direction:
            found.append("合成改写了某一份信号的方向")
    if decision.action != "观望" and (not decision.risk.get("signal_gate", {}).get("approved") or
                                        not any(v.income and v.risk and v.risk.approved for v in decision.verdicts)):
        found.append("最终动作未遵守信号或结构风控")
    deduped = []
    for item in found:
        if item not in deduped:
            deduped.append(item)
    return deduped


async def run(market, decision, runner=None, model: str | None = None) -> ReviewReport:
    if decision is None or not getattr(decision, "ok", False):
        return ReviewReport(ok=False, error="没有决策记录")
    found = findings_for(market, decision)
    report = ReviewReport(ok=True, ticker=decision.ticker, findings=found)
    if runner is None or not model:
        return report
    listed = "\n".join(found) if found else "无"
    prompt = (
        "你是 review 子 Agent。只核对下面这份 harness 已经查出的毛病清单。"
        "不要取数，不要改方向，不要新增清单里没有的毛病。"
        "verdict 在有毛病时填 fail，没有时填 pass。findings 照抄清单。\n\n"
        f"{listed}"
    )
    try:
        note, meta = await runner.run_json(
            AGENT, model, prompt, ReviewNote,
            output_schema={
                "type": "object",
                "properties": {
                    "verdict": {"type": "string"},
                    "findings": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["verdict", "findings"],
            },
        )
        del note
    except Exception as exc:
        report.ok = False
        report.error = str(exc)[:160]
        report.calls.append({"agent": AGENT, "thread_id": None, "usage": None, "error": str(exc)[:160]})
        return report
    usage = getattr(meta, "usage", None) if meta is not None else None
    thread_id = getattr(meta, "thread_id", None) if meta is not None else None
    report.calls.append({"agent": AGENT, "thread_id": thread_id, "usage": usage})
    return report


def run_public(ticker: str, trade_date: date | None = None) -> dict:
    from ..config import load_settings, parse_ticker
    from .decision import finalize_review

    day = trade_date or datetime.now(ZoneInfo("America/New_York")).date()
    parsed = parse_ticker(ticker)
    decision = session.get_decision(parsed.canonical, day)
    market = session.get_market(parsed.canonical, day)
    if decision is None or market is None:
        return {"ok": False, "agent": AGENT, "error": "没有决策记录"}
    report = asyncio.run(run(market, decision))
    decision = finalize_review(market, decision, report, load_settings())
    return {
        "ok": report.ok,
        "agent": report.agent,
        "ticker": report.ticker,
        "findings": report.findings,
        "verdict": "通过" if report.ok and not report.findings else "fail",
        "action": decision.action,
        "risk": decision.risk,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Review 子 Agent")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--date", default=None)
    args = parser.parse_args()
    day = date.fromisoformat(args.date) if args.date else datetime.now(ZoneInfo("America/New_York")).date()
    ticker = args.ticker if "." in args.ticker else f"US.{args.ticker}"
    decision = session.get_decision(ticker, day)
    market = session.get_market(ticker, day)
    if decision is None:
        print("没有决策记录")
        raise SystemExit(1)
    report = asyncio.run(run(market, decision))
    if report.findings:
        print("\n".join(report.findings))
    else:
        print("通过")


if __name__ == "__main__":
    main()
