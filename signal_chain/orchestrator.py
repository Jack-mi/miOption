"""Orchestrator：每标的完整链路编排。确定性代码，LLM 只出现在研究和简报环节。

用法:
  python -m signal_chain.orchestrator --tickers US.AAPL [--date 2026-09-23]
      [--no-llm] [--skip-report] [--bias bull|bear|neutral] [--shares 0]
"""

from __future__ import annotations

import argparse
import asyncio
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

from .agents.data import collect as collect_data
from .agents.decision import finalize_review, run as run_decision
from .agents.llm import LlmRunner
from .agents.review import run as run_review
from .config import RUNS_DIR, load_settings, parse_ticker
from .options.strategy_menu import render_menu
from .data.layer import clear_macro_cache
from .decision import render_signals
from .schema import EnsembleSignal
from .storage import RunLedger, append_signal, write_chain, write_coverage, write_report


def _fallback_report(ticker: str, ensemble: EnsembleSignal, proposals, decisions, snapshot=None) -> str:
    """Reporter agent 失败/跳过时的确定性简报。"""
    lines = [
        f"# {ticker} 期权决策简报（{ensemble.as_of}）",
        "",
        f"- 合成方向: **{ensemble.direction.value}**（强度 {ensemble.conviction:+.2f}，一致性 {ensemble.agreement}）",
        f"- 波动率视图: {ensemble.volatility_view}",
        f"- 数据质量: {ensemble.quality_notes or '报价与日线可核对'}",
        f"- 合成说明: {ensemble.synthesis_notes or '（无）'}",
    ]
    if snapshot is not None:
        lines += [
            "",
            "## 富途价格",
            f"- 报价: {snapshot.quote.meta.status}（{snapshot.quote.meta.as_of}）",
            f"- 日线: {snapshot.kline.meta.status}（最后交易日 {snapshot.kline.meta.as_of}）",
            f"- 技术: {snapshot.technical.meta.status}",
            f"- 除息: {snapshot.dividends.meta.status}"
            f"（下次 {snapshot.dividends.next_ex_date or '无公布'}）",
            f"- IV/HV 基准: {snapshot.vol_basis.meta.status}"
            f"（比值 {snapshot.vol_basis.ratio if snapshot.vol_basis.ratio is not None else '无'}）",
        ]
    if ensemble.dissent_summary:
        lines.append(f"- 分歧: {ensemble.dissent_summary}")
    lines += ["", "## 候选结构"]
    if not proposals:
        lines.append("- （无候选结构）")
    for p, d in zip(proposals, decisions):
        status = "结构检查通过（非收租晋级）" if d.approved else "否决: " + "; ".join(d.vetoes)
        lines.append(f"- **{p.name}** [{status}] {p.thesis}")
        for leg in p.legs:
            lines.append(f"  - {leg.side} {leg.code} {leg.option_type} K={leg.strike} exp={leg.expiry}")
    return "\n".join(lines) + "\n"


async def process_ticker(
    ticker_text: str,
    trade_date: date,
    runner: LlmRunner | None,
    ledger: RunLedger,
    *,
    skip_report: bool = False,
    bias: str | None = None,
    shares: int = 0,
) -> dict:
    settings = load_settings()
    models = settings.models
    t = parse_ticker(ticker_text)
    entry: dict = {"engines": {}, "agents": {}}
    entry["error"] = None  # 清掉上一次运行的陈旧错误（ledger 是合并语义）
    t0 = time.monotonic()
    model = models.get("synthesis")
    fetched = await collect_data(
        ticker_text, trade_date, settings, runner, model, include_chain=True,
    )
    entry["agents"]["data"] = fetched.calls or [
        {"agent": fetched.agent, "thread_id": None, "usage": None},
    ]
    if not fetched.ok or fetched.market is None:
        entry["error"] = fetched.text
        entry["elapsed_sec"] = round(time.monotonic() - t0, 1)
        ledger.record(t.canonical, entry)
        return entry
    market = fetched.market
    snapshot = market.snapshot
    write_coverage(trade_date, t.canonical, snapshot, sources=market.sources)
    entry["data_layer"] = [
        {"id": row.id, "field": row.field, "state": row.state, "note": row.note}
        for row in market.sources
    ]
    entry["macro"] = [
        {"series": point.series, "as_of": point.as_of.isoformat()}
        for point in market.macro
    ]
    entry["coverage"] = {
        "quote": snapshot.quote.meta.status,
        "kline": snapshot.kline.meta.status,
        "technical": snapshot.technical.meta.status,
        "capital_flow": snapshot.capital_flow.status,
        "fundamentals": snapshot.fundamentals.status,
        "news": snapshot.news.status,
        "dividends": snapshot.dividends.meta.status,
        "vol_basis": snapshot.vol_basis.meta.status,
    }

    decided = await run_decision(
        market, runner, settings, trade_date,
        bias=bias, shares=shares, trace_dir=RUNS_DIR / "research",
    )
    if not decided.ok or decided.ensemble is None:
        entry["error"] = decided.error or "没有决策记录"
        entry["elapsed_sec"] = round(time.monotonic() - t0, 1)
        ledger.record(t.canonical, entry)
        return entry
    signals = decided.signals
    for sig in signals:
        append_signal(trade_date, t.canonical, sig)
    entry["agents"].update(decided.agents)
    entry["signals"] = decided.signal_rows
    if decided.chain and decided.chain.get("error"):
        entry["chain"] = decided.chain
    elif market.chain is not None:
        write_chain(trade_date, t.canonical, market.chain)
        entry["chain"] = decided.chain
    ensemble = decided.ensemble
    append_signal(trade_date, t.canonical, ensemble)
    entry["ensemble"] = {
        "agreement": ensemble.agreement,
        "direction": ensemble.direction.value,
        "quality_notes": ensemble.quality_notes,
    }
    reviewed = await run_review(market, decided, runner, model)
    decided = finalize_review(market, decided, reviewed, settings)
    entry["risk"] = decided.risk
    proposals = decided.proposals
    decisions = decided.risk_decisions
    action = decided.action
    verdicts = decided.verdicts
    entry["agents"]["review"] = reviewed.calls or [
        {"agent": reviewed.agent, "thread_id": None, "usage": None},
    ]
    entry["review"] = {"ok": reviewed.ok, "findings": reviewed.findings}
    review_text = "完成既定机械检查（非交易保证）" if reviewed.ok and not reviewed.findings else "未通过：" + "；".join(reviewed.findings or [reviewed.error or "未知错误"])

    # 简报在 review 之后
    if runner is not None and not skip_report:
        prompt = (
            f"你是中文金融简报撰写人。根据以下材料写一份 {t.canonical} 的期权决策简报"
            f"（markdown，不超过 1000 字）：合成信号 {ensemble.model_dump_json()}；"
            f"决策动作 {action}。review：{review_text}。"
            "简报开头先用 150 字以内写合成说明：各引擎是否互相印证、各自的增量信息是什么；"
            "方向异号时再写一段分歧焦点。"
            "可以引用 review 的毛病清单，但不能把它改写成另一份判断。"
            "结构菜单会附在简报后面，不要改写其中的适合、不适合、做不了，也不要另造结构。"
            "简报正文不要写“未附结构菜单”或“不列结构”。"
            f"富途价格证据：报价 {snapshot.quote.meta.status} as_of {snapshot.quote.meta.as_of}，"
            f"日线 {snapshot.kline.meta.status} 最后交易日 {snapshot.kline.meta.as_of}，"
            f"技术 {snapshot.technical.meta.status}。"
            "简报先写富途快照状态，再写合成结论。"
            "三份信号已经单独成文，不要改写它们的方向、缺失和正文。"
            "data_status=opinion 的观点保留，但不得把该引擎报告里的 RSI、均线、财报日写成富途事实。"
            "agreement 为 insufficient_data 时结论必须写信号不足；"
            "不得把只有富途价格、引擎自身缺行情写成双源行情互证。"
        )
        try:
            rep = await runner.run_text("reporter", models["reporter"], prompt)
            markdown = rep.text
            entry["agents"]["reporter"] = {"thread_id": rep.meta.thread_id,
                                           "model": rep.meta.model}
        except Exception as exc:
            markdown = _fallback_report(t.canonical, ensemble, proposals, decisions, snapshot)
            entry["agents"]["reporter"] = {"error": str(exc)[:200]}
    else:
        markdown = _fallback_report(t.canonical, ensemble, proposals, decisions, snapshot)
    view = ""
    if bias or shares:
        word = {"bull": "看多", "bear": "看空", "neutral": "中性"}.get(bias or "", bias or "未改方向")
        view = (f"用户看法：**{word}**，自述持股 {shares}（未作为持仓凭证）。"
                "三份信号的方向没有改。\n\n")
    markdown = (
        f"决策动作：**{action}**。这条链路不下单。\n\n"
        f"数据状态：报价 {snapshot.quote.meta.status}（{snapshot.quote.meta.source}，市场时间 "
        f"{snapshot.quote.meta.market_time}，获取 {snapshot.quote.meta.fetched_at}）；"
        f"期权链 {decided.chain or '缺失'}；财报日期 {snapshot.earnings_date or '未知'}"
        f"（{snapshot.earnings_source or '无来源'}）；账户 "
        f"{'REAL/' + str(decided.risk['account_equity'].get('currency')) if decided.risk.get('account_equity') else '缺失'}"
        f"（获取 {decided.risk['account_equity'].get('fetched_at') if decided.risk.get('account_equity') else '未知'}）。\n\n"
        f"复核范围：{review_text}。\n\n"
        f"{view}"
        f"{render_signals(signals)}\n\n"
        f"{markdown}\n{render_menu(verdicts)}"
    )
    write_report(trade_date, t.canonical, markdown)

    entry["elapsed_sec"] = round(time.monotonic() - t0, 1)
    ledger.record(t.canonical, entry)
    return entry


def main() -> None:
    parser = argparse.ArgumentParser(description="signal_chain orchestrator")
    parser.add_argument("--tickers", default=None, help="逗号分隔，默认读 config watchlist")
    parser.add_argument("--date", default=datetime.now(ZoneInfo("America/New_York")).date().isoformat())
    parser.add_argument("--no-llm", action="store_true", help="跳过所有模型调用（纯确定性干跑）")
    parser.add_argument("--skip-report", action="store_true")
    parser.add_argument("--bias", choices=["bull", "bear", "neutral"], default=None)
    parser.add_argument("--shares", type=int, default=0)
    args = parser.parse_args()

    settings = load_settings()
    tickers = args.tickers.split(",") if args.tickers else settings.watchlist
    parsed = [parse_ticker(ticker) for ticker in tickers]
    if args.date:
        trade_date = date.fromisoformat(args.date)
    elif parsed and all(t.market == "HK" for t in parsed):
        trade_date = datetime.now(ZoneInfo("Asia/Hong_Kong")).date()
    else:
        trade_date = datetime.now(ZoneInfo("America/New_York")).date()
    ledger = RunLedger(trade_date)

    async def _run():
        runner = None if args.no_llm else LlmRunner()
        if runner is not None and not runner.api_key:
            runner = None
        if runner is None:
            for tk in tickers:
                await process_ticker(tk, trade_date, None, ledger,
                                     skip_report=args.skip_report,
                                     bias=args.bias, shares=args.shares)
        else:
            async with runner:
                for tk in tickers:
                    await process_ticker(tk, trade_date, runner, ledger,
                                         skip_report=args.skip_report,
                                         bias=args.bias, shares=args.shares)

    clear_macro_cache()
    asyncio.run(_run())
    print(f"done. ledger: {ledger.path}")


if __name__ == "__main__":
    main()
