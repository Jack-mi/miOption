"""数据源编辑器重算：纯确定性，不碰 LLM、不取数。

走势两分制（对齐 decision/signals.py trend_signal）：
价格 vs 5 日均线、资金净额正负；两项同向给 ±1，单侧 ±0.5，无分 0。
合成（对齐 synth/combine.py 规则 v5）：
投票者简单平均；同向且档位差 ≤1 时 ×1.2；仅一票 ×0.7；异号 conflicted。
"""

from __future__ import annotations

from . import paths
from .workbench import load_config

_SIGN = {"strong_buy": 1, "buy": 1, "neutral": 0, "sell": -1, "strong_sell": -1}
_TIER = {"strong_buy": 2, "buy": 1, "neutral": 0, "sell": -1, "strong_sell": -2}


def _dir_from(v: float) -> str:
    if v >= 0.6:
        return "strong_buy"
    if v >= 0.2:
        return "buy"
    if v > -0.2:
        return "neutral"
    if v > -0.6:
        return "sell"
    return "strong_sell"


def recompute_trend(quote: float | None, sma5: float | None, flow: float | None) -> dict:
    points: list[int] = []
    faces: list[str] = []
    if sma5 is not None and quote is not None:
        if quote > sma5:
            points.append(1)
            faces.append("技术面：价格在 5 日均线之上（+1）")
        elif quote < sma5:
            points.append(-1)
            faces.append("技术面：价格在 5 日均线之下（−1）")
        else:
            faces.append("技术面：价格等于 5 日均线，不计分")
    if flow is not None:
        if flow > 0:
            points.append(1)
            faces.append("资金面：净流入（+1）")
        elif flow < 0:
            points.append(-1)
            faces.append("资金面：净流出（−1）")
        else:
            faces.append("资金面：净额为零，不给分")
    if not points:
        direction, conviction, lead = "neutral", 0.0, "技术面和资金面都没有可计分的数，观望。"
    elif len(points) >= 2 and all(p > 0 for p in points):
        direction, conviction, lead = "strong_buy", 1.0, "技术面和资金面同向偏多。"
    elif len(points) >= 2 and all(p < 0 for p in points):
        direction, conviction, lead = "strong_sell", -1.0, "技术面和资金面同向偏空。"
    elif sum(points) > 0:
        direction, conviction, lead = "buy", 0.5, "已有的一面偏多。"
    elif sum(points) < 0:
        direction, conviction, lead = "sell", -0.5, "已有的一面偏空。"
    else:
        direction, conviction, lead = "neutral", 0.0, "已有的面没有方向。"
    return {"direction": direction, "conviction": conviction,
            "text": " ".join([lead, *faces]), "data_status": "actionable"}


def recompute_ensemble(trend: dict, others: list[dict]) -> dict:
    voting = [trend, *[o for o in others if o.get("data_status") != "insufficient_data"]]
    if not voting:
        return {"agreement": "insufficient_data", "direction": "neutral",
                "conviction": 0.0, "notes": "无可信报价或日线，信号弃权。"}
    if len(voting) == 1:
        conviction = round(voting[0]["conviction"] * 0.7, 4)
        agreement = "single_source"
    else:
        signs = [_SIGN.get(s["direction"], 0) for s in voting]
        tiers = [_TIER.get(s["direction"], 0) for s in voting]
        avg = sum(s["conviction"] for s in voting) / len(voting)
        if any(s > 0 for s in signs) and any(s < 0 for s in signs):
            agreement, conviction = "conflicted", round(avg, 4)
        elif any(s == 0 for s in signs) and any(s != 0 for s in signs):
            agreement, conviction = "partial", round(avg, 4)
        elif max(tiers) - min(tiers) <= 1:
            agreement = "aligned"
            conviction = round(max(-1.0, min(1.0, avg * 1.2)), 4)
        else:
            agreement, conviction = "partial", round(avg, 4)
    return {"agreement": agreement, "direction": _dir_from(conviction),
            "conviction": conviction,
            "notes": "按 combine.py 规则 v5 重算：对齐、弃权、上浮与单源折扣均已应用。"}


def recompute(ticker: str, overrides: dict) -> dict:
    """overrides: quote/sma5/sma20/flow/rsi14/iv30/earningsGap（可缺省=null）。"""
    cfg = load_config()
    risk = cfg.get("risk") or {}
    day = paths.latest_run_date()
    ledger = None
    if day:
        ledger = (paths.load_run(day).get("tickers") or {}).get(ticker)

    trend = recompute_trend(overrides.get("quote"), overrides.get("sma5"), overrides.get("flow"))
    others = []
    for row in (ledger or {}).get("signals") or []:
        if row.get("engine") in ("research", "value"):
            others.append({"direction": row.get("direction") or "neutral",
                           "conviction": row.get("conviction") or 0.0,
                           "data_status": row.get("data_status") or "insufficient_data"})
    ens = recompute_ensemble(trend, others)

    risk_notes: list[str] = []
    gap = overrides.get("earningsGap")
    blackout = risk.get("earnings_blackout_days", 10)
    if gap is not None and gap <= blackout:
        risk_notes.append(
            f"距下次财报 {gap} 天，落在 {blackout} 天窗口内，short-vol 结构将被否决。")
    min_conv = risk.get("min_conviction", 0.4)
    if abs(ens["conviction"]) < min_conv:
        risk_notes.append(
            f"合成强度 {ens['conviction']:.4f} 低于门槛 {min_conv}，信号闸将阻断。")

    return {
        "trend": trend,
        "ensemble": ens,
        "riskNotes": risk_notes,
        "notRecomputed": [
            "研究引擎：走模型，需重新请求，本轮沿用旧结论",
            "价值引擎：走财务流程 + 模型，需重新请求，本轮沿用旧结论",
            "结构菜单合约腿：来自真实期权链，改价后需重新取链确认",
        ],
        "limits": {"earnings_blackout_days": blackout, "min_conviction": min_conv},
    }
