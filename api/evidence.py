"""证据抽屉三个标签：字段覆盖矩阵 / 运行台账 / 阈值与账户。"""

from __future__ import annotations

from . import paths
from .fields import FIELD_DEFS, build_sources
from .workbench import build_console, load_config


def coverage_matrix(tickers: list[str]) -> dict:
    """字段覆盖矩阵：行 = 字段，列 = 标的。值是四态 + unknown。"""
    day = paths.latest_run_date()
    run = paths.load_run(day) if day else {"tickers": {}}
    cov_doc = paths.load_coverage(day) if day else {"tickers": {}}
    matrix: dict[str, dict[str, str]] = {}
    for t in tickers:
        ledger = (run.get("tickers") or {}).get(t)
        cov = (cov_doc.get("tickers") or {}).get(t)
        chain_meta = (ledger or {}).get("chain")
        states: dict[str, str] = {}
        for s in build_sources(t, day, ledger, cov, chain_meta):
            states[s["id"]] = s["state"]
        matrix[t] = states
    return {
        "date": day,
        "fields": [{"id": fid, "name": name} for fid, name, _c, _s in FIELD_DEFS],
        "tickers": tickers,
        "matrix": matrix,
    }


def run_ledger(ticker: str) -> dict:
    day = paths.latest_run_date()
    run = paths.load_run(day) if day else {"tickers": {}}
    ledger = (run.get("tickers") or {}).get(ticker)
    if ledger is None:
        return {"date": day, "ticker": ticker, "hasLedger": False}
    agents = ledger.get("agents") or {}
    agent_rows = []
    for group in ("data", "research", "review"):
        for row in agents.get(group) or []:
            agent_rows.append({
                "agent": row.get("agent") or group,
                "thread_id": row.get("thread_id"),
                "input_tokens": (row.get("usage") or {}).get("input_tokens"),
                "output_tokens": (row.get("usage") or {}).get("output_tokens"),
            })
    reporter = agents.get("reporter")
    if reporter:
        agent_rows.append({
            "agent": "reporter",
            "thread_id": reporter.get("thread_id"),
            "model": reporter.get("model"),
        })
    risk = ledger.get("risk") or {}
    engines = ledger.get("engines") or {}
    if not engines:
        # 台账没记引擎状态时从信号 data_status 推导
        for row in ledger.get("signals") or []:
            st = row.get("data_status")
            engines[row.get("engine")] = (
                "ok" if st == "actionable" else "opinion" if st == "opinion" else "abstain")
    return {
        "date": day,
        "ticker": ticker,
        "hasLedger": True,
        "engines": engines,
        "elapsed_sec": ledger.get("elapsed_sec"),
        "updated_at": ledger.get("updated_at"),
        "agents": agent_rows,
        "ensemble": ledger.get("ensemble"),
        "signal_gate": risk.get("signal_gate"),
        "action": risk.get("decision"),
        "review": risk.get("review") or ledger.get("review"),
        "macro": ledger.get("macro") or [],
        "data_layer": ledger.get("data_layer") or [],
    }


def risk_panel(ticker: str) -> dict:
    cfg = load_config()
    console = build_console(ticker)
    menu = console["menu"]
    decided = [m for m in menu if m.get("approved") is not None or m.get("risk")]
    vetoed = [m for m in decided if m.get("approved") is False
              or (m.get("risk") and not m["risk"].get("approved"))]
    return {
        "ticker": ticker,
        "limits": cfg.get("risk") or {},
        "account_equity": console["risk"].get("account_equity"),
        "checked": len(decided),
        "vetoed": [{"name": m["name"],
                    "vetoes": m.get("vetoes") or (m.get("risk") or {}).get("vetoes") or []}
                   for m in vetoed],
        "review": console["risk"].get("review"),
        "signal_gate": console["risk"].get("signal_gate"),
    }


def strategies() -> list[dict]:
    """27 张百科笔记：knowledge/wiki/strategies/*.md + 方向组/场景元数据。"""
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from signal_chain.options.glossary import _NOTES, strategy_blurb

    # 方向组与市场/风险/希腊字母元数据（展示层，来自策略笔记属性）
    meta = _strategy_meta()
    out = []
    for name, filename in _NOTES.items():
        path = paths.STRATEGIES_DIR / filename
        if not path.is_file():
            continue
        group, en, market, risk, greeks = meta.get(name, ("neutral", filename[:-3], "", "", ""))
        out.append({
            "name": name,
            "en": en,
            "file": filename,
            "group": group,
            "blurb": strategy_blurb(name),
            "market": market,
            "risk": risk,
            "greeks": greeks,
        })
    return out


def _strategy_meta() -> dict[str, tuple[str, str, str, str, str]]:
    """name → (group, en, market, risk, greeks)。"""
    return {
        "买入看涨": ("bull", "Long Call", "看多", "有限", "Δ+ Γ+ V+"),
        "牛市看涨价差": ("bull", "Bull Call Spread", "温和看多", "有限", "Δ+ V±"),
        "牛市认沽价差": ("bull", "Bull Put Spread", "看多或横盘", "有限", "Δ+ V−"),
        "现金担保认沽": ("bull", "Cash-Secured Put", "看多或愿承接", "有限（担保）", "Δ+ V−"),
        "认购日历价差": ("bull", "Long Call Calendar Spread", "横盘", "有限", "V+ Θ+"),
        "对角认购价差": ("bull", "Diagonal Call Spread", "温和看多", "有限", "Δ+ V+"),
        "带式": ("bull", "Strap", "波动偏多", "有限", "Δ+ V+"),
        "裸卖看跌": ("bull", "Naked Put", "看多", "大（无担保）", "Δ+ V−"),
        "买入看跌": ("bear", "Long Put", "看空", "有限", "Δ− Γ+ V+"),
        "熊市认沽价差": ("bear", "Bear Put Spread", "温和看空", "有限", "Δ− V±"),
        "熊市看涨价差": ("bear", "Bear Call Spread", "看空或横盘", "有限", "Δ− V−"),
        "裸卖看涨": ("bear", "Naked Call", "看空", "无上限", "Δ− V−"),
        "条式": ("bear", "Strip", "波动偏空", "有限", "Δ− V+"),
        "买入跨式": ("neutral", "Long Straddle", "大波动", "有限", "V+ Γ+"),
        "买入宽跨": ("neutral", "Long Strangle", "大波动", "有限", "V+ Γ+"),
        "卖出跨式": ("neutral", "Short Straddle", "窄幅横盘", "无上限", "V− Θ+"),
        "卖出宽跨": ("neutral", "Short Strangle", "横盘", "无上限", "V− Θ+"),
        "卖出铁鹰": ("neutral", "Iron Condor", "区间震荡", "有限", "V− Θ+"),
        "卖出铁蝶": ("neutral", "Short Iron Butterfly", "窄幅横盘", "有限", "V− Θ+"),
        "买入认购蝶式": ("neutral", "Long Call Butterfly", "窄幅看多", "有限", "Θ+ V−"),
        "买入认沽蝶式": ("neutral", "Long Put Butterfly", "窄幅看空", "有限", "Θ+ V−"),
        "买入认购鹰式": ("neutral", "Long Call Condor", "区间偏多", "有限", "Θ+ V−"),
        "买入认沽鹰式": ("neutral", "Long Put Condor", "区间偏空", "有限", "Θ+ V−"),
        "认沽日历价差": ("neutral", "Long Put Calendar Spread", "横盘偏空", "有限", "V+ Θ+"),
        "保护性认沽": ("hedge", "Protective Put", "持有正股", "有限", "Δ− V+"),
        "备兑看涨": ("hedge", "Covered Call", "持有正股", "有限", "V− Θ+"),
        "领口": ("hedge", "Collar", "持有正股", "有限", "V±"),
    }


def field_detail(ticker: str, field_id: str) -> dict:
    """单个字段的惰性详情：只算被点开的那个。任何异常都不能拖垮页面。"""
    try:
        return _field_detail(ticker, field_id)
    except Exception as exc:
        return {"rows": [["status", "unavailable"]], "note": str(exc)}


def _field_detail(ticker: str, field_id: str) -> dict:
    console = build_console(ticker)
    src = next((s for s in console["sources"] if s["id"] == field_id), None)
    if src is None:
        return {"rows": [["status", "unknown"]], "note": ""}
    if src["state"] == "unknown":
        return {"rows": [["status", "unknown"]], "note": "台账里没有这只标的的运行记录。"}

    q = console["quote"]
    rows: list[list] = []
    note = src.get("note") or ""
    if field_id == "quote":
        rows = [
            ["last", f"{q['spot']} {console['currency']}" if q["spot"] is not None else "missing"],
            ["prev_close", q["prevClose"] if q["prevClose"] is not None else "missing"],
            ["currency", console["currency"]],
            ["market_time", q.get("market_time") or "—"],
            ["source", q.get("source") or "—"],
        ]
    elif field_id == "kline":
        bars = console["bars"]
        rows = [
            ["adjusted", "true"],
            ["bars", len(bars)],
            ["first", bars[0]["trade_date"] if bars else "missing"],
            ["last", bars[-1]["trade_date"] if bars else "missing"],
        ]
    elif field_id == "technical":
        t = console["technical"]
        rows = [
            ["sma_5", t.get("sma_5") if t.get("sma_5") is not None else "missing"],
            ["sma_20", t.get("sma_20") if t.get("sma_20") is not None else "missing"],
            ["rsi_14", t.get("rsi_14") if t.get("rsi_14") is not None else "missing"],
            ["atr_14", t.get("atr_14") if t.get("atr_14") is not None else "missing"],
        ]
    elif field_id == "chain":
        c = console["chain"]
        if c:
            rows = [["rows", c["rows"]], ["source", c["source"]],
                    ["degraded", "true" if c["degraded"] else "false"],
                    ["expiries", len(c["expiries"])]]
        else:
            rows = [["status", "missing"]]
    elif field_id == "account":
        acct = console["risk"].get("account_equity") or {}
        rows = [
            ["env", acct.get("env") or "—"],
            ["currency", acct.get("currency") or "—"],
            ["value", round(acct["value"], 2) if acct.get("value") is not None else "missing"],
            ["available_cash", acct.get("available_cash") if acct.get("available_cash") is not None else "missing"],
            ["fetched_at", acct.get("fetched_at") or "—"],
        ]
    elif field_id == "earnings":
        rows = [["earnings_date", console["earningsDate"] or "missing"]]
    elif field_id == "vol_basis":
        vb = console.get("volBasis") or {}
        rows = [
            ["iv30", vb.get("iv30") if vb.get("iv30") is not None else "missing"],
            ["iv_rank", vb.get("ivRank") if vb.get("ivRank") is not None else "missing"],
            ["hv_latest", vb.get("hv_latest") if vb.get("hv_latest") is not None else "missing"],
            ["iv_hv_ratio", vb.get("iv_hv_ratio") if vb.get("iv_hv_ratio") is not None else "missing"],
            ["points", vb.get("points", "missing")],
            ["as_of", vb.get("as_of", "missing")],
        ]
    else:
        rows = [["status", src["state"]], ["source", src.get("source") or "—"]]
        if src.get("error"):
            rows.append(["error", src["error"][:200]])
    return {"rows": rows, "note": note}
