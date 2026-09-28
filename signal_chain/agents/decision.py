"""研究决策子 Agent。不取数。三份信号、合成、结构菜单和风控到此结束。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..decision import build_signals, to_engine_signal
from ..options.iv import derive_volatility_view
from ..options.strategy_menu import apply_user_bias, decision_action, screen_menu
from ..research.berkshire import earnings_catalyst
from ..risk.account_equity import read_account_equity
from ..risk.limits import check_signal
from ..synth.combine import combine
from . import session

AGENT = "decision"


@dataclass
class DecisionReport:
    ok: bool
    agent: str = AGENT
    ticker: str = ""
    signals: list = field(default_factory=list)
    bundles: list = field(default_factory=list)
    ensemble: object | None = None
    verdicts: list = field(default_factory=list)
    action: str = ""
    proposals: list = field(default_factory=list)
    risk_decisions: list = field(default_factory=list)
    agents: dict = field(default_factory=dict)
    signal_rows: list = field(default_factory=list)
    risk: dict = field(default_factory=dict)
    chain: dict | None = None
    error: str = ""


async def run(
    market,
    runner,
    settings,
    trade_date: date,
    *,
    bias: str | None = None,
    shares: int = 0,
    trace_dir=None,
) -> DecisionReport:
    if market is None:
        return DecisionReport(ok=False, error="没有快照")
    ticker = market.snapshot.ticker
    models = settings.models
    selected = await build_signals(
        market, runner, models.get("synthesis"), trace_dir=trace_dir,
    )
    signals = []
    agents: dict = {}
    rows = []
    for bundle in selected:
        sig = to_engine_signal(bundle)
        if bundle.meta.get("calls"):
            agents[bundle.engine] = bundle.meta["calls"]
        signals.append(sig)
        rows.append({
            "engine": sig.engine,
            "direction": sig.direction.value,
            "conviction": sig.conviction,
            "data_status": sig.data_status,
            "faces": sig.quality_notes,
            "gaps": list(sig.data_gaps),
            "analysis": sig.reasoning,
        })
    syn_cfg = settings.synthesis
    ensemble = combine(
        signals, as_of=trade_date,
        aligned_boost=syn_cfg["aligned_boost"],
        single_source_discount=syn_cfg["single_source_discount"],
        max_asof_gap_days=syn_cfg["max_asof_gap_days"],
    )
    chain = market.chain
    chain_meta = None
    if market.chain_error:
        chain_meta = {"error": market.chain_error}
    elif chain is not None:
        chain_meta = {"source": chain.source, "rows": len(chain.rows), "degraded": chain.degraded}
    ensemble = ensemble.model_copy(update={
        "volatility_view": derive_volatility_view(ensemble, chain),
    })
    earnings = earnings_catalyst(market.snapshot)
    if earnings is not None:
        ensemble = ensemble.model_copy(update={"catalysts": [*ensemble.catalysts, earnings]})
    risk_cfg = settings.risk
    account = read_account_equity(market.snapshot.market, settings) if risk_cfg.get("auto_account_equity") else None
    sig_gate = check_signal(ensemble)
    verdicts = screen_menu(
        apply_user_bias(ensemble, bias), chain,
        holds_shares=shares >= 100,
        account_equity=account["value"] if account else None,
        equity_currency=account["currency"] if account else None,
        equity_note=account.get("note") if account else None,
        earnings_blackout_days=risk_cfg["earnings_blackout_days"],
        min_open_interest=risk_cfg["min_open_interest"],
        max_spread_pct=risk_cfg["max_spread_pct"],
        max_position_risk_pct=risk_cfg["max_position_risk_pct"],
        today=trade_date,
    )
    proposals = [v.proposal for v in verdicts if v.proposal is not None]
    risk_decisions = [v.risk for v in verdicts if v.risk is not None]
    action = decision_action(verdicts)
    risk = {
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
        risk["decline_reason"] = "; ".join(sig_gate.vetoes)
    report = DecisionReport(
        ok=True, ticker=ticker, signals=signals, bundles=selected, ensemble=ensemble,
        verdicts=verdicts, action=action, proposals=proposals, risk_decisions=risk_decisions,
        agents=agents, signal_rows=rows, risk=risk, chain=chain_meta,
    )
    session.put_decision(ticker, trade_date, report)
    return report


def run_public(ticker: str, trade_date: date | None = None) -> dict:
    import asyncio

    from ..config import load_settings, parse_ticker

    day = trade_date or date.today()
    parsed = parse_ticker(ticker)
    market = session.get_market(parsed.canonical, day)
    if market is None:
        return {"ok": False, "agent": AGENT, "error": "没有快照"}
    report = asyncio.run(run(market, None, load_settings(), day))
    return {
        "ok": report.ok,
        "agent": report.agent,
        "ticker": report.ticker,
        "action": report.action,
        "signals": report.signal_rows,
        "error": report.error,
    }
