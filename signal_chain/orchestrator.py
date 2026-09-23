"""Orchestrator：每标的完整链路编排。确定性代码，LLM 只在 pipeline.steps 里出现。

用法:
  python -m signal_chain.orchestrator --tickers US.AAPL,HK.00700 [--date 2026-09-23]
      [--engines-only] [--use-existing] [--no-codex] [--skip-report]
"""

from __future__ import annotations

import argparse
import asyncio
import time
from datetime import date

from .adapters import DsaAdapter, TaAdapter
from .agents.codex import CodexAgentRunner
from .config import DSA_DIR, load_settings, parse_ticker
from .engines.runner import EngineRunResult, run_engines_parallel
from .options.chain_fetch import fetch_chain
from .options.iv import derive_volatility_view
from .pipeline.steps import extract_signal, propose_strategies, synthesize_notes
from .risk.limits import check_proposal, check_signal
from .risk.account_equity import read_account_equity
from .schema import EngineSignal, EnsembleSignal, make_signal_id
from .storage import RunLedger, append_signal, write_chain, write_report
from .synth.combine import combine


def _fallback_report(ticker: str, ensemble: EnsembleSignal, proposals, decisions) -> str:
    """Reporter agent 失败/跳过时的确定性简报。"""
    lines = [
        f"# {ticker} 期权决策简报（{ensemble.as_of}）",
        "",
        f"- 合成方向: **{ensemble.direction.value}**（强度 {ensemble.conviction:+.2f}，一致性 {ensemble.agreement}）",
        f"- 波动率视图: {ensemble.volatility_view}",
        f"- 合成说明: {ensemble.synthesis_notes or '（无）'}",
    ]
    if ensemble.dissent_summary:
        lines.append(f"- 分歧: {ensemble.dissent_summary}")
    lines += ["", "## 成分信号"]
    for c in ensemble.components:
        flag = "（降级）" if c.degraded else ""
        lines.append(f"- [{c.engine}] {c.direction.value} {c.conviction:+.2f}{flag}: {c.reasoning[:200]}")
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
    runner: CodexAgentRunner | None,
    ledger: RunLedger,
    *,
    engines_only: bool = False,
    use_existing: bool = False,
    skip_report: bool = False,
) -> dict:
    settings = load_settings()
    models = settings.models
    t = parse_ticker(ticker_text)
    entry: dict = {"engines": {}, "agents": {}}
    entry["error"] = None  # 清掉上一次运行的陈旧错误（ledger 是合并语义）
    t0 = time.monotonic()

    # 1. 引擎并行（或复用既有产物）
    if use_existing:
        results: dict[str, EngineRunResult] = {}
        ta_dir = settings.ta_results_dir() / f"{trade_date.isoformat()}_{t.canonical.replace('.', '-')}"
        ta_state = ta_dir / "state.json"
        dsa_report = DSA_DIR / "reports" / f"report_{trade_date.strftime('%Y%m%d')}.md"
        if ta_state.exists():
            results["tradingagents"] = EngineRunResult(
                "tradingagents", True, out_dir=ta_dir, report_path=ta_state)
        if dsa_report.exists():
            results["dsa"] = EngineRunResult("dsa", True, report_path=dsa_report)
    else:
        results = await run_engines_parallel(t, trade_date, settings)
    for name, r in results.items():
        entry["engines"][name] = {"ok": r.ok, "error": r.error,
                                  "elapsed_sec": round(r.elapsed_sec, 1)}
    ledger.record(t.canonical, entry)

    # 2. 适配
    bundles = []
    if results.get("tradingagents") and results["tradingagents"].ok:
        bundles.append(TaAdapter().load(
            results["tradingagents"].report_path, t, trade_date,
            llm_model=f"{models['ta_deep_think']}/{models['ta_quick_think']}"))
    if results.get("dsa") and results["dsa"].ok:
        bundles.append(DsaAdapter().load(
            results["dsa"].report_path, t, trade_date, llm_model=models["dsa"]))
    valid = [b for b in bundles if b.valid]
    if not valid:
        entry["error"] = "无有效引擎信号（全部失败或评级作废）"
        ledger.record(t.canonical, entry)
        return entry
    if engines_only:
        entry["engines_only"] = True
        entry["bundles"] = [
            {"engine": b.engine, "direction": b.direction.value if b.direction else None,
             "conviction": b.conviction, "report_ref": b.report_ref}
            for b in valid
        ]
        ledger.record(t.canonical, entry)
        return entry

    # 3. [CODEX] 抽取 -> EngineSignal
    signals: list[EngineSignal] = []
    for b in valid:
        if runner is not None:
            sig, meta = await extract_signal(runner, b, models["extraction"])
            if meta:
                entry["agents"][f"extract:{b.engine}"] = {
                    "thread_id": meta.thread_id, "model": meta.model,
                    "elapsed_ms": meta.elapsed_ms, "attempts": meta.attempts}
        else:
            sig = EngineSignal(
                signal_id=make_signal_id(b.engine, b.ticker, b.as_of, seed=b.report_ref),
                engine=b.engine, raw_report_ref=b.report_ref,
                data_sources=b.data_sources, llm_model=b.llm_model,
                ticker=b.ticker, market=b.market, as_of=b.as_of,
                direction=b.direction, conviction=b.conviction,
                reasoning=" ".join(b.texts.values())[:500], degraded=True,
                quality_notes="no-codex 模式：跳过抽取 agent")
        signals.append(sig)
        append_signal(trade_date, t.canonical, sig)

    # 4. 规则合成
    syn_cfg = settings.synthesis
    ensemble = combine(
        signals, as_of=trade_date,
        aligned_boost=syn_cfg["aligned_boost"],
        single_source_discount=syn_cfg["single_source_discount"],
        max_asof_gap_days=syn_cfg["max_asof_gap_days"],
    )

    # 5. 取链 + IV 派生
    chain = None
    try:
        chain = fetch_chain(t, settings)
        write_chain(trade_date, t.canonical, chain)
        entry["chain"] = {"source": chain.source, "rows": len(chain.rows),
                          "degraded": chain.degraded}
    except Exception as exc:
        entry["chain"] = {"error": str(exc)[:300]}
    ensemble = ensemble.model_copy(update={
        "volatility_view": derive_volatility_view(ensemble, chain)})

    # 6. [CODEX] 合成说明
    if runner is not None:
        ensemble, meta = await synthesize_notes(runner, ensemble, models["synthesis"])
        if meta:
            entry["agents"]["synthesize"] = {"thread_id": meta.thread_id,
                                             "model": meta.model}
    append_signal(trade_date, t.canonical, ensemble)

    # 7. 风控信号闸 -> [CODEX] 策略 -> 风控结构闸
    proposals, decisions, decline = [], [], None
    sig_gate = check_signal(ensemble)
    entry["risk"] = {"signal_gate": sig_gate.model_dump(mode="json")}
    if not sig_gate.approved:
        decline = "; ".join(sig_gate.vetoes)
    elif runner is not None and chain is not None:
        proposals, decline, meta = await propose_strategies(
            runner, ensemble, chain, models["strategy"])
        if meta:
            entry["agents"]["strategy"] = {"thread_id": meta.thread_id,
                                           "model": meta.model}
        risk_cfg = settings.risk
        account = read_account_equity(t.market, settings) if risk_cfg.get("auto_account_equity") else None
        entry["risk"]["account_equity"] = account
        for p in proposals:
            d = check_proposal(
                p, ensemble, chain,
                earnings_blackout_days=risk_cfg["earnings_blackout_days"],
                min_open_interest=risk_cfg["min_open_interest"],
                max_spread_pct=risk_cfg["max_spread_pct"],
                account_equity=account["value"] if account else None,
                equity_currency=account["currency"] if account else None,
                max_position_risk_pct=risk_cfg["max_position_risk_pct"])
            decisions.append(d)
        entry["risk"]["proposals"] = [
            {"name": p.name, "approved": d.approved,
             "vetoes": d.vetoes, "warnings": d.warnings}
            for p, d in zip(proposals, decisions)
        ]
    if decline:
        entry["risk"]["decline_reason"] = decline

    # 8. 简报
    if runner is not None and not skip_report:
        prompt = (
            f"你是中文金融简报撰写人。根据以下材料写一份 {t.canonical} 的期权决策简报"
            f"（markdown，不超过 600 字）：合成信号 {ensemble.model_dump_json()}；"
            f"候选结构 {[p.model_dump(mode='json') for p in proposals]}；"
            f"风控结果 {[d.model_dump(mode='json') for d in decisions]}；"
            f"未提议原因 {decline}。"
            "要求：先说结论，再说证据，风险条目逐条列出，禁止编造材料外的数字。"
        )
        try:
            rep = await runner.run_text("reporter", models["reporter"], prompt)
            markdown = rep.text
            entry["agents"]["reporter"] = {"thread_id": rep.meta.thread_id,
                                           "model": rep.meta.model}
        except Exception as exc:
            markdown = _fallback_report(t.canonical, ensemble, proposals, decisions)
            entry["agents"]["reporter"] = {"error": str(exc)[:200]}
    else:
        markdown = _fallback_report(t.canonical, ensemble, proposals, decisions)
    write_report(trade_date, t.canonical, markdown)

    entry["elapsed_sec"] = round(time.monotonic() - t0, 1)
    ledger.record(t.canonical, entry)
    return entry


def main() -> None:
    parser = argparse.ArgumentParser(description="signal_chain orchestrator")
    parser.add_argument("--tickers", default=None, help="逗号分隔，默认读 config watchlist")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--engines-only", action="store_true", help="只跑引擎+适配（M0 用）")
    parser.add_argument("--use-existing", action="store_true", help="复用既有引擎产物，不重跑")
    parser.add_argument("--no-codex", action="store_true", help="跳过所有 Codex agent（纯确定性干跑）")
    parser.add_argument("--skip-report", action="store_true")
    args = parser.parse_args()

    settings = load_settings()
    trade_date = date.fromisoformat(args.date)
    tickers = args.tickers.split(",") if args.tickers else settings.watchlist
    ledger = RunLedger(trade_date)

    async def _run():
        if args.no_codex:
            for tk in tickers:
                await process_ticker(tk, trade_date, None, ledger,
                                     engines_only=args.engines_only,
                                     use_existing=args.use_existing,
                                     skip_report=args.skip_report)
        else:
            async with CodexAgentRunner() as runner:
                for tk in tickers:
                    await process_ticker(tk, trade_date, runner, ledger,
                                         engines_only=args.engines_only,
                                         use_existing=args.use_existing,
                                         skip_report=args.skip_report)

    asyncio.run(_run())
    print(f"done. ledger: {ledger.path}")


if __name__ == "__main__":
    main()
