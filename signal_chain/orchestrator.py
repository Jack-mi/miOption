"""Orchestrator：每标的完整链路编排。确定性代码，LLM 只在 pipeline.steps 里出现。

用法:
  python -m signal_chain.orchestrator --tickers US.AAPL [--date 2026-09-23]
      [--no-llm] [--skip-report] [--bias bull|bear|neutral] [--shares 0]
"""

from __future__ import annotations

import argparse
import asyncio
import time
from datetime import date

from .agents.llm import LlmRunner
from .config import RUNS_DIR, load_settings, parse_ticker
from .options.iv import derive_volatility_view
from .options.strategy_menu import apply_user_bias, decision_action, render_menu, screen_menu
from .data.layer import clear_macro_cache, load as load_market
from .decision import build_signals, render_signals, to_engine_signal
from .pipeline.steps import synthesize_notes
from .risk.limits import check_signal
from .risk.account_equity import read_account_equity
from .research.berkshire import earnings_catalyst
from .schema import Direction, EngineSignal, EnsembleSignal, make_signal_id
from .storage import RunLedger, append_signal, write_chain, write_coverage, write_report
from .synth.combine import combine


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
        ]
    if ensemble.dissent_summary:
        lines.append(f"- 分歧: {ensemble.dissent_summary}")
    lines += ["", "## 候选结构"]
    if not proposals:
        lines.append("- （无候选结构）")
    for p, d in zip(proposals, decisions):
        status = "通过" if d.approved else "否决: " + "; ".join(d.vetoes)
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
    market = load_market(t, trade_date, settings, include_chain=True)
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
    }

    selected = await build_signals(
        market, runner, models.get("synthesis"),
        trace_dir=RUNS_DIR / "research",
    )

    signals: list[EngineSignal] = []
    for b in selected:
        sig = to_engine_signal(b)
        if b.meta.get("calls"):
            entry["agents"][b.engine] = b.meta["calls"]
        signals.append(sig)
        append_signal(trade_date, t.canonical, sig)
    entry["signals"] = [
        {
            "engine": sig.engine,
            "direction": sig.direction.value,
            "conviction": sig.conviction,
            "data_status": sig.data_status,
            "faces": sig.quality_notes,
            "gaps": list(sig.data_gaps),
            "analysis": sig.reasoning,
        }
        for sig in signals
    ]

    # 4. 规则合成
    syn_cfg = settings.synthesis
    ensemble = combine(
        signals, as_of=trade_date,
        aligned_boost=syn_cfg["aligned_boost"],
        single_source_discount=syn_cfg["single_source_discount"],
        max_asof_gap_days=syn_cfg["max_asof_gap_days"],
    )

    # 5. 取链 + IV 派生
    chain = market.chain
    if market.chain_error:
        entry["chain"] = {"error": market.chain_error}
    elif chain is not None:
        write_chain(trade_date, t.canonical, chain)
        entry["chain"] = {"source": chain.source, "rows": len(chain.rows),
                          "degraded": chain.degraded}
    ensemble = ensemble.model_copy(update={
        "volatility_view": derive_volatility_view(ensemble, chain)})
    earnings = earnings_catalyst(snapshot)
    if earnings is not None:
        ensemble = ensemble.model_copy(update={
            "catalysts": [*ensemble.catalysts, earnings]})

    # 6. [CODEX] 合成说明
    if runner is not None:
        ensemble, meta = await synthesize_notes(runner, ensemble, models["synthesis"])
        if meta:
            entry["agents"]["synthesize"] = {"thread_id": meta.thread_id,
                                             "model": meta.model}
    append_signal(trade_date, t.canonical, ensemble)
    entry["ensemble"] = {
        "agreement": ensemble.agreement,
        "direction": ensemble.direction.value,
        "quality_notes": ensemble.quality_notes,
    }

    # 7. 结构菜单：27 项先给结论，过关的才选合约并过风控。不再让模型挑结构。
    risk_cfg = settings.risk
    account = read_account_equity(t.market, settings) if risk_cfg.get("auto_account_equity") else None
    sig_gate = check_signal(ensemble)
    verdicts = screen_menu(
        apply_user_bias(ensemble, bias), chain,
        holds_shares=shares >= 100,
        account_equity=account["value"] if account else None,
        equity_currency=account["currency"] if account else None,
        earnings_blackout_days=risk_cfg["earnings_blackout_days"],
        min_open_interest=risk_cfg["min_open_interest"],
        max_spread_pct=risk_cfg["max_spread_pct"],
        max_position_risk_pct=risk_cfg["max_position_risk_pct"],
        today=trade_date,
    )
    proposals = [v.proposal for v in verdicts if v.proposal is not None]
    decisions = [v.risk for v in verdicts if v.risk is not None]
    action = decision_action(verdicts)
    entry["risk"] = {
        "signal_gate": sig_gate.model_dump(mode="json"),
        "account_equity": account,
        "decision": action,
        "menu": [
            {
                "name": v.name, "status": v.status, "reason": v.reason,
                "approved": None if v.risk is None else v.risk.approved,
                "vetoes": [] if v.risk is None else v.risk.vetoes,
                "max_loss": None if v.proposal is None else v.proposal.max_loss,
            }
            for v in verdicts
        ],
    }
    if not sig_gate.approved:
        entry["risk"]["decline_reason"] = "; ".join(sig_gate.vetoes)

    # 8. 简报
    if runner is not None and not skip_report:
        prompt = (
            f"你是中文金融简报撰写人。根据以下材料写一份 {t.canonical} 的期权决策简报"
            f"（markdown，不超过 600 字）：合成信号 {ensemble.model_dump_json()}；"
            f"决策动作 {action}。"
            "结构菜单会附在简报后面，不要改写其中的适合、不适合、做不了，也不要另造结构。"
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
        view = f"用户看法：**{word}**，持股 {shares}。三份信号的方向没有改。\n\n"
    markdown = (
        f"决策动作：**{action}**。这条链路不下单。\n\n"
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
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--no-llm", action="store_true", help="跳过所有模型调用（纯确定性干跑）")
    parser.add_argument("--skip-report", action="store_true")
    parser.add_argument("--bias", choices=["bull", "bear", "neutral"], default=None)
    parser.add_argument("--shares", type=int, default=0)
    args = parser.parse_args()

    settings = load_settings()
    trade_date = date.fromisoformat(args.date)
    tickers = args.tickers.split(",") if args.tickers else settings.watchlist
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
