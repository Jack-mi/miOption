"""研究决策子 Agent。不取数。三份信号、合成、结构菜单和风控到此结束。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone

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
    bias: str | None = None


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
    earnings = earnings_catalyst(market.snapshot)
    if earnings is not None:
        ensemble = ensemble.model_copy(update={"catalysts": [*ensemble.catalysts, earnings]})
    ensemble = ensemble.model_copy(update={
        "volatility_view": derive_volatility_view(ensemble, chain, today=trade_date),
    })
    risk_cfg = settings.risk
    account = read_account_equity(market.snapshot.market, settings) if risk_cfg.get("auto_account_equity") else None
    sig_gate = check_signal(ensemble)
    held = sum(float(row.get("can_sell_qty") or 0) for row in (account or {}).get("positions", [])
               if row.get("code") == ticker)
    closes = [(bar.trade_date, bar.close) for bar in market.snapshot.kline.bars]
    biased = apply_user_bias(ensemble, bias)
    verdicts = screen_menu(
        biased, chain,
        holds_shares=held >= 100,
        account_equity=account["value"] if account else None,
        equity_currency=account["currency"] if account else None,
        equity_note=account.get("note") if account else None,
        earnings_blackout_days=risk_cfg["earnings_blackout_days"],
        min_open_interest=risk_cfg["min_open_interest"],
        max_spread_pct=risk_cfg["max_spread_pct"],
        max_position_risk_pct=risk_cfg["max_position_risk_pct"],
        today=trade_date,
        account=account, closes=closes, signal_ok=sig_gate.approved, review_ok=False,
        now=datetime.now(timezone.utc), config=risk_cfg,
        earnings_date=market.snapshot.earnings_date,
        signal_direction=biased.direction,
    )
    proposals = [v.proposal for v in verdicts if v.proposal is not None]
    risk_decisions = [v.risk for v in verdicts if v.risk is not None]
    action = "观望"
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
                "tier": v.tier,
                "income": v.income,
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
        bias=bias,
    )
    session.put_decision(ticker, trade_date, report)
    return report


def finalize_review(market, decision: DecisionReport, review, settings) -> DecisionReport:
    """Only the reviewed decision can be promoted; never use an old snapshot as authority."""
    reviewed = bool(review.ok and not review.findings)
    chain = market.chain
    account = decision.risk.get("account_equity")
    signal_ok = bool(decision.risk.get("signal_gate", {}).get("approved"))
    settings_risk = settings.risk
    biased = apply_user_bias(decision.ensemble, decision.bias)
    verdicts = screen_menu(
        biased, chain,
        account_equity=account.get("value") if account else None,
        equity_currency=account.get("currency") if account else None,
        equity_note=account.get("note") if account else None,
        holds_shares=any(row.get("code") == decision.ticker and
                         float(row.get("can_sell_qty") or 0) >= 100
                         for row in (account or {}).get("positions", [])),
        account=account,
        closes=[(bar.trade_date, bar.close) for bar in market.snapshot.kline.bars],
        signal_ok=signal_ok, review_ok=reviewed,
        today=decision.ensemble.as_of, now=datetime.now(timezone.utc), config=settings_risk,
        earnings_date=market.snapshot.earnings_date,
        signal_direction=biased.direction,
        earnings_blackout_days=settings_risk["earnings_blackout_days"],
        min_open_interest=settings_risk["min_open_interest"],
        max_spread_pct=settings_risk["max_spread_pct"],
        max_position_risk_pct=settings_risk["max_position_risk_pct"],
    )
    decision.verdicts = verdicts
    decision.proposals = [v.proposal for v in verdicts if v.proposal is not None]
    decision.risk_decisions = [v.risk for v in verdicts if v.risk is not None]
    decision.action = decision_action(verdicts) if reviewed and signal_ok else "观望"
    decision.risk["decision"] = decision.action
    decision.risk["review"] = {"ok": reviewed, "findings": review.findings}
    decision.risk["menu"] = [
        {"name": v.name, "status": v.status, "reason": v.reason, "tier": v.tier,
         "income": v.income, "approved": None if v.risk is None else v.risk.approved,
         "vetoes": [] if v.risk is None else v.risk.vetoes,
         "max_loss": None if v.proposal is None else v.proposal.max_loss}
        for v in verdicts
    ]
    session.put_decision(decision.ticker, decision.ensemble.as_of, decision)
    return decision


def run_public(ticker: str, trade_date: date | None = None) -> dict:
    import asyncio
    from zoneinfo import ZoneInfo

    from ..config import load_settings, parse_ticker

    day = trade_date or datetime.now(ZoneInfo("America/New_York")).date()
    parsed = parse_ticker(ticker)
    market = session.fresh_market(parsed.canonical, day)
    if market is None:
        return {"ok": False, "agent": AGENT, "error": "没有快照"}
    report = asyncio.run(run(market, None, load_settings(), day))
    return {
        "ok": report.ok,
        "agent": report.agent,
        "ticker": report.ticker,
        "action": report.action,
        "signals": report.signal_rows,
        "risk": report.risk,
        "error": report.error,
    }
