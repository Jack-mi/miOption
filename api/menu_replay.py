"""菜单腿重放：台账 risk.menu[] 只有 name/status/tier/income/max_loss/vetoes，
没有合约腿。用链快照 + ledger 的 signal rows 重跑 combine + screen_menu，
把 proposal.legs 补回来用于展示。

纪律：台账是状态/档位/vetoes/max_loss 的权威；重放只补腿与 income 数值。
重放与台账不一致或腿重构失败 → 该行降级为不可展开。
"""

from __future__ import annotations

import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(REPO_ROOT), str(REPO_ROOT / "runtime")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

log = logging.getLogger("mioption.menu_replay")


def _build_engine_signals(ticker: str, rows: list[dict], as_of: date):
    from signal_chain.schema import Direction, EngineSignal

    out = []
    market = ticker.split(".", 1)[0]
    for row in rows:
        engine = row.get("engine") or "unknown"
        try:
            direction = Direction(row.get("direction") or "neutral")
        except ValueError:
            direction = Direction.NEUTRAL
        out.append(EngineSignal(
            signal_id=f"{engine}-{ticker}-{as_of.isoformat()}-replay",
            engine=engine,
            raw_report_ref=engine,
            ticker=ticker,
            market=market,
            as_of=as_of,
            direction=direction,
            conviction=float(row.get("conviction") or 0.0),
            reasoning=row.get("analysis") or "",
            data_status=row.get("data_status") or "actionable",
            data_gaps=list(row.get("gaps") or []),
            degraded=(row.get("data_status") == "insufficient_data"),
        ))
    return out


def replay_menu(
    ticker: str,
    day: str,
    ledger: dict,
    chain_doc: dict | None,
    risk_cfg: dict,
    synthesis_cfg: dict,
) -> dict[str, dict]:
    """{菜单项 name: 重放结果}。任何失败记 warning 返回 {}，绝不阻断页面。"""
    try:
        return _replay(ticker, day, ledger, chain_doc, risk_cfg, synthesis_cfg)
    except Exception as exc:  # 一处兜底：重放失败只丢腿，不丢页面
        log.warning("menu replay failed for %s@%s: %s", ticker, day, exc)
        return {}


def _load_chain(chain_doc: dict | None):
    from signal_chain.schema import ChainSnapshot

    return ChainSnapshot.model_validate(chain_doc) if chain_doc else None


def _replay(ticker, day, ledger, chain_doc, risk_cfg, synthesis_cfg):
    from signal_chain.data.daily_store import DailyStore
    from signal_chain.options.iv import derive_volatility_view
    from signal_chain.options.strategy_menu import screen_menu
    from signal_chain.synth.combine import combine

    as_of = date.fromisoformat(day)
    signals = _build_engine_signals(ticker, ledger.get("signals") or [], as_of)
    if not signals:
        return {}
    ensemble = combine(
        signals, as_of=as_of,
        aligned_boost=synthesis_cfg.get("aligned_boost", 1.2),
        single_source_discount=synthesis_cfg.get("single_source_discount", 0.7),
        max_asof_gap_days=synthesis_cfg.get("max_asof_gap_days", 1),
    )
    chain = _load_chain(chain_doc)
    ensemble = ensemble.model_copy(update={
        "volatility_view": derive_volatility_view(
            ensemble, chain, today=as_of,
            iv_hv_rising_ratio=risk_cfg.get("iv_hv_rising_ratio", 1.15),
        ),
    })

    account = (ledger.get("risk") or {}).get("account_equity")
    gate = (ledger.get("risk") or {}).get("signal_gate") or {}
    review = (ledger.get("risk") or {}).get("review") or {}

    closes: list[tuple[date, float]] = []
    try:
        bars = DailyStore().read(ticker, "futu", True, as_of)
        closes = [
            (date.fromisoformat(str(b["trade_date"])[:10]), float(b["close"]))
            for b in bars if b.get("close") is not None
        ]
    except Exception as exc:
        log.info("daily store unavailable for %s: %s", ticker, exc)

    contract_size = 100
    if chain:
        sizes = [r.contract_size for r in chain.rows if r.contract_size]
        if sizes:
            contract_size = min(sizes)
    held = sum(
        float(row.get("can_sell_qty") or 0)
        for row in (account or {}).get("positions", [])
        if row.get("code") == ticker
    )
    verdicts = screen_menu(
        ensemble, chain,
        holds_shares=held >= contract_size,
        account_equity=account.get("value") if account else None,
        equity_currency=account.get("currency") if account else None,
        equity_note=account.get("note") if account else None,
        earnings_blackout_days=risk_cfg.get("earnings_blackout_days", 10),
        ex_div_blackout_days=risk_cfg.get("ex_div_blackout_days", 5),
        min_open_interest=risk_cfg.get("min_open_interest", 100),
        max_spread_pct=risk_cfg.get("max_spread_pct", 0.10),
        max_position_risk_pct=risk_cfg.get("max_position_risk_pct", 0.05),
        today=as_of,
        account=account,
        closes=closes,
        signal_ok=bool(gate.get("approved")),
        review_ok=bool(review.get("ok")),
        now=datetime.now(timezone.utc),
        config=risk_cfg,
        earnings_date=None,
        signal_direction=ensemble.direction,
        evidence_ok=True,
    )

    out: dict[str, list[dict]] = {}
    for v in verdicts:
        entry: dict = {"replay_status": v.status, "replay_tier": v.tier}
        if v.proposal is not None:
            p = v.proposal
            by_code = {r.code: r for r in chain.rows} if chain else {}
            legs = []
            for leg in p.legs:
                row = by_code.get(leg.code)
                legs.append({
                    "code": leg.code,
                    "option_type": leg.option_type,
                    "strike": leg.strike,
                    "expiry": leg.expiry.isoformat(),
                    "side": leg.side,
                    "quantity": leg.quantity,
                    "bid": row.bid if row else None,
                    "ask": row.ask if row else None,
                    "open_interest": row.open_interest if row else None,
                    "iv": row.iv if row else None,
                    "delta": row.delta if row else None,
                })
            entry.update({
                "legs": legs,
                "net_premium": p.net_premium,
                "max_profit": p.max_profit,
                "is_short_vol": p.is_short_vol,
                "notes": p.notes,
                "thesis": p.thesis,
            })
        if v.risk is not None:
            entry["risk"] = {
                "approved": v.risk.approved,
                "vetoes": list(v.risk.vetoes),
                "warnings": list(v.risk.warnings),
            }
        if v.income:
            entry["income"] = v.income
        # 同名结构可出现多次（收租 ranked 取前 3），按序保留，与台账逐条对应
        out.setdefault(v.name, []).append(entry)
    return out
