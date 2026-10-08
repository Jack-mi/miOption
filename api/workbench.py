"""console / watchlist / evidence 聚合。全部只读，数据来自文件系统产物。"""

from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

import yaml

from . import paths
from .fields import build_sources, research_claims
from .menu_replay import replay_menu

log = logging.getLogger("mioption.workbench")

REPO_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(REPO_ROOT), str(REPO_ROOT / "runtime")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 结构中文名 → 方向组 / 英文名（对齐 options/strategy_menu.CATALOG 与 glossary._NOTES）
MENU_GROUPS: dict[str, tuple[str, str]] = {
    "买入看涨": ("bull", "Long Call"),
    "买入看跌": ("bear", "Long Put"),
    "裸卖看涨": ("bear", "Naked Call"),
    "裸卖看跌": ("bull", "Naked Put"),
    "保护性认沽": ("hedge", "Protective Put"),
    "牛市看涨价差": ("bull", "Bull Call Spread"),
    "牛市认沽价差": ("bull", "Bull Put Spread"),
    "熊市看涨价差": ("bear", "Bear Call Spread"),
    "熊市认沽价差": ("bear", "Bear Put Spread"),
    "备兑看涨": ("hedge", "Covered Call"),
    "现金担保认沽": ("bull", "Cash-Secured Put"),
    "领口": ("hedge", "Collar"),
    "买入跨式": ("neutral", "Long Straddle"),
    "卖出跨式": ("neutral", "Short Straddle"),
    "买入宽跨": ("neutral", "Long Strangle"),
    "卖出宽跨": ("neutral", "Short Strangle"),
    "带式": ("bull", "Strap"),
    "条式": ("bear", "Strip"),
    "认购日历价差": ("bull", "Long Call Calendar Spread"),
    "认沽日历价差": ("neutral", "Long Put Calendar Spread"),
    "对角认购价差": ("bull", "Diagonal Call Spread"),
    "买入认购蝶式": ("neutral", "Long Call Butterfly"),
    "买入认沽蝶式": ("neutral", "Long Put Butterfly"),
    "买入认购鹰式": ("neutral", "Long Call Condor"),
    "买入认沽鹰式": ("neutral", "Long Put Condor"),
    "卖出铁蝶": ("neutral", "Short Iron Butterfly"),
    "卖出铁鹰": ("neutral", "Iron Condor"),
}

ENGINE_LABELS = {"trend": "走势", "research": "研究", "value": "价值"}
ENGINE_KINDS = {
    "trend": "确定性规则 · 无模型",
    "research": "模型判定 · deepseek-flash",
    "value": "财务流程 + 模型 · deepseek-flash",
}


def load_config() -> dict:
    with open(paths.CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def list_tickers() -> list[dict]:
    """观察清单标的 = config watchlist ∪ 最新 runs ∪ seller 卡标的。"""
    cfg = load_config()
    day = paths.latest_run_date()
    run = paths.load_run(day) if day else None
    tickers: list[str] = []
    for t in cfg.get("watchlist") or []:
        if t not in tickers:
            tickers.append(t)
    for t in (run or {}).get("tickers") or {}:
        if t not in tickers:
            tickers.append(t)
    for t in _seller_tickers():
        if t not in tickers:
            tickers.append(t)
    out = []
    for t in tickers:
        ledger = (run or {}).get("tickers", {}).get(t)
        out.append({"ticker": t, "hasLedger": ledger is not None,
                    "badge": _ticker_badge(ledger)})
    return out


def _ticker_badge(ledger: dict | None) -> str:
    if ledger is None:
        return "报价缺失"
    ens = ledger.get("ensemble") or {}
    agreement = ens.get("agreement")
    if agreement == "conflicted":
        return "方向分歧"
    if agreement == "insufficient_data":
        return "数据不足"
    cov = ledger.get("coverage") or {}
    if cov.get("quote") == "missing":
        return "报价缺失"
    conviction = _recomputed_conviction(ledger)
    if conviction is not None and abs(conviction) < 0.4:
        return "强度不足"
    if agreement == "single_source":
        return "单源"
    return "信号可用"


def _recomputed_conviction(ledger: dict) -> float | None:
    """台账 ensemble 没存 conviction，按 combine v5 规则从 signal rows 复核补齐。"""
    rows = [r for r in (ledger.get("signals") or []) if r.get("data_status") != "insufficient_data"]
    if not rows:
        return 0.0 if (ledger.get("ensemble") or {}).get("agreement") == "insufficient_data" else None
    sign = {"strong_buy": 1, "buy": 1, "neutral": 0, "sell": -1, "strong_sell": -1}
    tier = {"strong_buy": 2, "buy": 1, "neutral": 0, "sell": -1, "strong_sell": -2}
    if len(rows) == 1:
        return round(rows[0].get("conviction", 0.0) * 0.7, 4)
    avg = sum(r.get("conviction", 0.0) for r in rows) / len(rows)
    signs = [sign.get(r.get("direction"), 0) for r in rows]
    tiers = [tier.get(r.get("direction"), 0) for r in rows]
    if any(s > 0 for s in signs) and any(s < 0 for s in signs):
        return round(avg, 4)
    if any(s == 0 for s in signs) and any(s != 0 for s in signs):
        return round(avg, 4)
    if max(tiers) - min(tiers) <= 1:
        return round(max(-1.0, min(1.0, avg * 1.2)), 4)
    return round(avg, 4)


def _seller_tickers() -> list[str]:
    out: list[str] = []
    sig_dir = paths.SELLER_DIR / "signals"
    if not sig_dir.is_dir():
        return out
    for path in sorted(sig_dir.glob("*.json")):
        t = path.name.split("-")[0]
        if t and t not in out:
            out.append(t)
    return out


def build_console(ticker: str) -> dict:
    """决策台聚合：一次返回 00–04 全部区块。"""
    cfg = load_config()
    risk_cfg = cfg.get("risk") or {}
    syn_cfg = cfg.get("synthesis") or {}
    day = paths.latest_run_date()
    run = paths.load_run(day) if day else {"tickers": {}}
    ledger = (run.get("tickers") or {}).get(ticker)
    cov_doc = paths.load_coverage(day) if day else {"tickers": {}}
    cov = (cov_doc.get("tickers") or {}).get(ticker)
    chain_doc = paths.load_chain(day, ticker) if day else None

    market = ticker.split(".", 1)[0]
    currency = (cov or {}).get("currency") or ("HKD" if market == "HK" else "USD")

    quote_meta = (cov or {}).get("quote") or {}
    spot = chain_doc.get("spot") if chain_doc else None

    closes = _daily_closes(ticker, day)
    prev_close = closes[-1][1] if closes else None
    bars = [{"trade_date": d.isoformat(), "close": c} for d, c in closes[-60:]]

    technical = _technical_from_closes(closes) if (cov or {}).get("technical", {}).get("status") == "available" else {}

    chain_summary = None
    if chain_doc:
        chain_summary = {
            "spot": chain_doc.get("spot"),
            "rows": len(chain_doc.get("rows") or []),
            "source": chain_doc.get("source"),
            "degraded": bool(chain_doc.get("degraded")),
            "fetched_at": chain_doc.get("fetched_at"),
            "spot_at": chain_doc.get("spot_at"),
            "expiries": sorted({r["expiry"] for r in chain_doc.get("rows") or []}),
            "iv_by_expiry": _iv_by_expiry(chain_doc),
        }

    signals = _build_signals(ticker, day, ledger, market)
    ensemble = _build_ensemble(ledger, signals)

    previews: dict[str, str | None] = {}
    if quote_meta.get("status") == "available" and spot is not None:
        previews["quote"] = f"{spot} {currency}"
    if chain_summary:
        previews["chain"] = f"{chain_summary['rows']} 行 · " + ("已降级" if chain_summary["degraded"] else "未降级")
    sources = build_sources(ticker, day, ledger, cov, chain_summary, previews)

    menu = list(_build_menu(ticker, day, ledger, chain_doc, risk_cfg, syn_cfg))

    report_md = paths.load_report(day, ticker) if (ledger and day) else None
    risk = (ledger or {}).get("risk") or {}

    vol_basis = paths.load_vol_basis(ticker)

    result = {
        "ticker": ticker,
        "market": market,
        "currency": currency,
        "asOf": day,
        "hasLedger": ledger is not None,
        "quote": {
            "spot": spot,
            "prevClose": prev_close,
            "status": quote_meta.get("status") or ("missing" if ledger else "unknown"),
            "source": quote_meta.get("source"),
            "as_of": quote_meta.get("as_of"),
            "market_time": quote_meta.get("market_time"),
        },
        "technical": technical,
        "bars": bars,
        "earningsDate": _earnings_date(cov),
        "sources": sources,
        "signals": signals,
        "ensemble": ensemble,
        "chain": chain_summary,
        "menu": menu,
        "risk": {
            "signal_gate": risk.get("signal_gate"),
            "account_equity": risk.get("account_equity"),
            "review": risk.get("review"),
            "decision": risk.get("decision"),
            "limits": risk_cfg,
        },
        "report": {"markdown": report_md, "date": day} if report_md else None,
        "cards": build_cards(ticker),
        "volBasis": vol_basis,
    }
    # 结构化中文简报：按固定大纲用台账数据生成，全中文。
    # 原始 reporter 文件仍保留在 reports/{date}/{ticker}.md，不改写。
    from .report import build_report
    result["reportStructured"] = build_report(result)
    return result


def _daily_closes(ticker: str, day: str | None) -> list[tuple[date, float]]:
    try:
        from signal_chain.data.daily_store import DailyStore
        until = date.fromisoformat(day) if day else date.today()
        bars = DailyStore().read(ticker, "futu", True, until)
        dedup: dict[date, float] = {}
        for b in bars:
            if b.get("close") is None:
                continue
            dedup[date.fromisoformat(str(b["trade_date"])[:10])] = float(b["close"])
        return sorted(dedup.items())
    except Exception as exc:
        log.info("daily closes unavailable for %s: %s", ticker, exc)
        return []


def _sma(values: list[float], n: int) -> float | None:
    if len(values) < n:
        return None
    return round(sum(values[-n:]) / n, 4)


def _technical_from_closes(closes: list[tuple[date, float]]) -> dict:
    vals = [c for _, c in closes]
    out: dict = {"sma_5": _sma(vals, 5), "sma_20": _sma(vals, 20),
                 "rsi_14": None, "atr_14": None}
    if len(vals) >= 15:
        gains, losses = [], []
        for i in range(-14, 0):
            chg = vals[i] - vals[i - 1]
            gains.append(max(chg, 0.0))
            losses.append(max(-chg, 0.0))
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        if avg_loss > 0:
            out["rsi_14"] = round(100 - 100 / (1 + avg_gain / avg_loss), 2)
        elif avg_gain > 0:
            out["rsi_14"] = 100.0
        trs = [abs(closes[i][1] - closes[i - 1][1]) for i in range(-14, 0)]
        out["atr_14"] = round(sum(trs) / 14, 4)
    return out


def _iv_by_expiry(chain_doc: dict) -> list[dict]:
    spot = chain_doc.get("spot")
    rows = chain_doc.get("rows") or []
    as_of = chain_doc.get("as_of")
    try:
        base = date.fromisoformat(as_of) if as_of else None
    except ValueError:
        base = None
    out = []
    for expiry in sorted({r["expiry"] for r in rows}):
        ex_rows = [r for r in rows if r["expiry"] == expiry]
        atm_iv = None
        if spot is not None:
            near = sorted(
                (r for r in ex_rows if r.get("iv") and r["iv"] > 0),
                key=lambda r: abs(r["strike"] - spot),
            )[:3]
            if near:
                atm_iv = round(sum(r["iv"] for r in near) / len(near), 4)
        spreads = []
        for r in ex_rows:
            bid, ask = r.get("bid"), r.get("ask")
            if bid and ask and bid > 0 and ask > 0:
                mid = (bid + ask) / 2
                if mid > 0:
                    spreads.append((ask - bid) / mid)
        spreads.sort()
        spread_pct = round(spreads[len(spreads) // 2], 4) if spreads else None
        oi = sum(r.get("open_interest") or 0 for r in ex_rows)
        dte = None
        if base:
            try:
                dte = (date.fromisoformat(expiry) - base).days
            except ValueError:
                pass
        out.append({"expiry": expiry, "dte": dte, "atm_iv": atm_iv,
                    "spread_pct": spread_pct, "oi": oi})
    return out


def _build_signals(ticker: str, day: str | None, ledger: dict | None, market: str) -> dict:
    claims = research_claims(day, ticker) if (ledger and day) else []
    out = {}
    rows = {r.get("engine"): r for r in (ledger or {}).get("signals") or []}
    for engine in ("trend", "research", "value"):
        row = rows.get(engine)
        status = (row or {}).get("data_status") or ("insufficient_data" if ledger else "unknown")
        out[engine] = {
            "signal_id": f"{engine}-{ticker}-{day}-ledger" if ledger else f"{engine}-{ticker}-none",
            "engine": engine,
            "engineLabel": ENGINE_LABELS[engine],
            "engine_kind": ENGINE_KINDS[engine],
            "direction": (row or {}).get("direction") or "neutral",
            "conviction": (row or {}).get("conviction") if status != "insufficient_data" else 0,
            "data_status": status,
            "reasoning": (row or {}).get("analysis") or "",
            "claims": claims if engine == "value" else [],
            "risk_flags": [],
            "volatility_view": "unknown",
            "data_gaps": list((row or {}).get("gaps") or []),
            "faces": (row or {}).get("faces") or "",
            "llm_model": None if engine == "trend" else "deepseek-flash",
            "as_of": day,
            "ticker": ticker,
            "market": market,
        }
    return out


def _build_ensemble(ledger: dict | None, signals: dict) -> dict:
    if not ledger:
        return {
            "agreement": "insufficient_data", "direction": "neutral",
            "conviction": 0.0, "volatility_view": "unknown",
            "quality_notes": "台账里没有这只标的的运行记录",
            "catalysts": [], "dissent_summary": None, "components": [],
        }
    ens = ledger.get("ensemble") or {}
    conviction = _recomputed_conviction(ledger)
    return {
        "agreement": ens.get("agreement") or "insufficient_data",
        "direction": ens.get("direction") or "neutral",
        "conviction": conviction if conviction is not None else 0.0,
        "volatility_view": "unknown",
        "quality_notes": ens.get("quality_notes"),
        "catalysts": [],
        "dissent_summary": None,
        "components": [
            {"engine": s["engine"], "direction": s["direction"],
             "conviction": s["conviction"], "data_status": s["data_status"]}
            for s in signals.values()
        ],
    }


def _earnings_date(cov: dict | None) -> str | None:
    if not cov:
        return None
    es = cov.get("earnings_source")
    if isinstance(es, dict) and es.get("status") == "available":
        return es.get("earnings_date") or es.get("as_of")
    return None


def _build_menu(ticker, day, ledger, chain_doc, risk_cfg, syn_cfg) -> list[dict]:
    ledger_menu = ((ledger or {}).get("risk") or {}).get("menu") or []
    if not ledger_menu:
        for name, (group, en) in MENU_GROUPS.items():
            out_item = {"name": name, "nameEn": en, "group": group,
                        "status": "impossible", "reason": "台账里没有运行记录，菜单不可评估。",
                        "tier": None, "income": None, "max_loss": None,
                        "vetoes": [], "approved": None, "expandable": False,
                        "legs": None, "net_premium": None, "max_profit": None,
                        "is_short_vol": None, "notes": None, "risk": None}
            yield out_item
        return
    replay = replay_menu(ticker, day, ledger, chain_doc, risk_cfg, syn_cfg)
    replay_idx: dict[str, int] = {}
    for item in ledger_menu:
        name = item.get("name") or ""
        group, en = MENU_GROUPS.get(name, ("neutral", name))
        # 同名多条（收租 ranked）按出现顺序一一对应
        idx = replay_idx.get(name, 0)
        replay_idx[name] = idx + 1
        rep_list = replay.get(name) or []
        rep = rep_list[idx] if idx < len(rep_list) else {}
        status = item.get("status") or "unfit"
        # 一致性检查：重放与台账不一致 → 该行降级不可展开，台账为准
        consistent = True
        if rep.get("replay_status") and rep["replay_status"] != status:
            consistent = False
            log.warning("menu replay mismatch %s %s: ledger=%s replay=%s",
                        ticker, name, status, rep["replay_status"])
        expandable = bool(consistent and rep.get("legs"))
        yield {
            "name": name, "nameEn": en, "group": group,
            "status": status,
            "reason": item.get("reason") or "",
            "tier": item.get("tier"),
            "income": item.get("income"),
            "max_loss": item.get("max_loss"),
            "vetoes": list(item.get("vetoes") or []),
            "approved": item.get("approved"),
            "expandable": expandable,
            "legs": rep.get("legs") if expandable else None,
            "net_premium": rep.get("net_premium") if expandable else None,
            "max_profit": rep.get("max_profit") if expandable else None,
            "is_short_vol": rep.get("is_short_vol") if expandable else None,
            "notes": rep.get("notes") if expandable else None,
            "risk": rep.get("risk") if expandable else None,
        }


# ---------------- seller 候选卡 ----------------

STRUCTURE_NAMES = {
    "bull_put_spread": ("牛市认沽价差", "Bull Put Spread"),
    "bear_call_spread": ("熊市看涨价差", "Bear Call Spread"),
}


def build_cards(ticker: str) -> list[dict]:
    """该标的的 seller 候选卡；历史卡降级「仅观察」并追加理由（只改展示）。"""
    import json as _json
    from datetime import datetime, timezone

    sig_dir = paths.SELLER_DIR / "signals"
    if not sig_dir.is_dir():
        return []
    marks_dir = paths.SELLER_DIR / "marks"
    today = datetime.now(timezone.utc).date()
    out = []
    for path in sorted(sig_dir.glob(f"{ticker}-*.json")):
        try:
            raw = _json.loads(path.read_text(encoding="utf-8"))
        except (OSError, _json.JSONDecodeError):
            continue
        if raw.get("underlying") != ticker:
            continue
        card = dict(raw)
        verdict = card.get("verdict")
        mark_path = marks_dir / f"{card['id']}.json"
        if mark_path.is_file():
            try:
                mark = _json.loads(mark_path.read_text(encoding="utf-8"))
                verdict = mark.get("verdict") or None
            except (OSError, _json.JSONDecodeError):
                pass
        created = (card.get("created_at") or "")[:10]
        historical = True
        if created:
            try:
                historical = date.fromisoformat(created) < today
            except ValueError:
                historical = True
        tier = card.get("tier") or "仅观察"
        reasons = list(card.get("tier_reasons") or [])
        if historical and tier != "禁做":
            tier = "仅观察"
            if "历史卡片需重取盘口及决策证据" not in reasons:
                reasons.append("历史卡片需重取盘口及决策证据")
        zh, en = STRUCTURE_NAMES.get(card.get("structure_id"), (card.get("structure_id"), ""))
        max_loss = card.get("max_loss")
        out.append({
            "id": card["id"],
            "ticker": ticker,
            "structure": card.get("structure_id"),
            "name": zh,
            "nameEn": en,
            "expiry": card.get("expiry"),
            "dte": card.get("dte"),
            "spot": card.get("spot"),
            "short": card.get("short"),
            "long": card.get("long"),
            "credit": card.get("credit"),
            "width": card.get("width"),
            "max_profit": card.get("max_profit"),
            "max_loss": max_loss,
            "breakeven": card.get("breakeven"),
            "return_on_risk": (card.get("max_profit") / max_loss) if (card.get("max_profit") and max_loss) else None,
            "tier": tier,
            "reasons": reasons,
            "blocking": [],
            "verdict": verdict,
            "quote_source": card.get("quote_source"),
            "quoted_at": card.get("quoted_at"),
            "created_at": card.get("created_at"),
            "historical": historical,
            "wiki_path": card.get("wiki_path"),
        })
    out.sort(key=lambda c: (c["created_at"] or "", c["id"]), reverse=True)
    return out


def save_verdict(card_id: str, verdict: str | None) -> dict:
    """唯一写接口：与 CLI 同一份真相（apply_verdict → save_card + save_mark）。"""
    from runtime.mioption_runtime.seller.monitor import apply_verdict
    from runtime.mioption_runtime.seller.store import SellerStore

    store = SellerStore(root=paths.SELLER_DIR)
    if verdict is None:
        return apply_verdict(store, card_id, "clear")
    if verdict not in ("adopt", "watch", "reject"):
        return {"ok": False, "error": "bad_verdict",
                "allowed": ["adopt", "watch", "reject", None]}
    return apply_verdict(store, card_id, verdict)


# ---------------- 观察清单 ----------------

def build_watchlist() -> dict:
    rows = []
    for t in list_tickers():
        console = build_console(t["ticker"])
        ens = console["ensemble"]
        usable = ens["agreement"] not in ("conflicted", "insufficient_data")
        gate = console["risk"].get("signal_gate") or {}
        rows.append({
            "ticker": t["ticker"],
            "hasLedger": t["hasLedger"],
            "badge": t["badge"],
            "spot": console["quote"]["spot"],
            "prevClose": console["quote"]["prevClose"],
            "currency": console["currency"],
            "direction": ens["direction"],
            "conviction": ens["conviction"],
            "agreement": ens["agreement"],
            "volatility_view": ens["volatility_view"],
            "iv30": (console.get("volBasis") or {}).get("iv30"),
            "ivRank": (console.get("volBasis") or {}).get("ivRank"),
            "earningsDate": console["earningsDate"],
            "cards": len(console["cards"]),
            "gateApproved": bool(gate.get("approved")),
            "gateVetoes": gate.get("vetoes") or [],
            "usable": usable,
            # 错价窗口：IV 分位 ≥55、非 conflicted/insufficient、|conviction| ≥0.3
            "mispriceWindow": bool(
                usable
                and (console.get("volBasis") or {}).get("ivRank") is not None
                and console["volBasis"]["ivRank"] >= 0.55
                and abs(ens["conviction"]) >= 0.3
            ),
        })
    return {"rows": rows}
