"""数据层字段：把 coverage.json / 台账 / 研究包映射成设计稿的字段网格。

状态语义（与 CHECKLIST 一致）：
  available / missing / unsupported / stale —— 来自 FieldMeta 或 sources[] 原样透传
  unknown —— 台账里没有这只标的，第五态，不是 missing
绝不把缺字段补 0。
"""

from __future__ import annotations

import json

from .paths import RUNS_DIR

# (id, 中文名, 契约说明, 期望来源)。顺序即页面顺序。
FIELD_DEFS: list[tuple[str, str, str, str]] = [
    ("quote", "报价", "富途 get_market_snapshot，单源；非 available 不得携带价格", "futu"),
    ("kline", "复权日线", "富途 request_history_kline，前复权；末根交易日须等于 as_of", "futu"),
    ("technical", "技术指标", "sma_5 / sma_20 / rsi_14 / atr_14 由日线推导，不单独否决", "derived"),
    ("capital_flow", "资金流", "富途 in_flow；成交额不冒称主力净流入", "futu"),
    ("fundamentals", "基本面", "两源差 <1% 才写入 ratios，单源留 facts 不标可用", "futu/fmp/edgar"),
    ("news", "新闻", "只作旁证，不改方向，不进分数", "futu/finnhub"),
    ("dividends", "除息", "未来除息用于提前指派风险门禁", "futu_dividends"),
    ("vol_basis", "波动率基差", "IV/HV 比值，仅链判不出方向时兜底", "futu_vol_basis"),
    ("social", "社交", "本轮不接入即 unsupported，与 missing 语气分开", "—"),
    ("business", "商业模式", "研究包字段；缺失保持写缺失，不推断", "edgar/morningstar"),
    ("competition", "竞争格局", "行业/对手/份额无字段时不推断", "—"),
    ("risk", "风险", "研究包字段；正文不借给财务工人", "edgar/morningstar"),
    ("governance", "治理", "研究包未拆分独立治理字段，并入风险包", "—"),
    ("events", "事件", "只认 events.json 映射；赔率不进决策", "polymarket"),
    ("macro", "宏观", "Supabase macro_latest 共享层，不随标的重复取 FRED", "supabase"),
    ("earnings", "财报日", "未确认就写未确认；EDGAR 申报日只留备注", "futu/edgar/nasdaq"),
    ("chain", "期权链", "富途主源，失败降级 Cboe 延迟链；结构只引用真实合约", "futu/cboe"),
    ("account", "账户权益", "REAL 账户只读；读不到告警并跳过亏损上限检查", "futu"),
]

# coverage.json 里直接带 FieldMeta 的字段
_COVERAGE_DIRECT = {
    "quote", "kline", "technical", "capital_flow",
    "fundamentals", "news", "dividends", "vol_basis",
}

_SOURCE_STATE = {
    "used": "available",
    "missing": "missing",
    "unsupported": "unsupported",
    "skipped": "unsupported",
}


def _from_sources(sources: list[dict], field: str) -> dict | None:
    """sources[] 里某字段的代表行：used > missing > unsupported > skipped。"""
    rows = [s for s in sources if s.get("field") == field]
    if not rows:
        return None
    for want in ("used", "missing", "unsupported", "skipped"):
        for row in rows:
            if row.get("state") == want:
                return row
    return rows[0]


def _research_doc(day: str, ticker: str) -> dict:
    path = RUNS_DIR / "research" / f"{day}_{ticker.replace('.', '-')}.jsonl"
    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.loads(f.readline())
    except (json.JSONDecodeError, OSError):
        return {}


def research_claims(day: str, ticker: str) -> list[str]:
    claims = _research_doc(day, ticker).get("accepted_claims")
    return claims if isinstance(claims, list) else []


def build_sources(
    ticker: str,
    day: str,
    ledger: dict | None,
    coverage: dict | None,
    chain_meta: dict | None,
    previews: dict[str, str | None] | None = None,
) -> list[dict]:
    """返回字段网格。ledger=None 时全部 unknown（第五态）。"""
    previews = previews or {}
    if ledger is None:
        return [
            {
                "id": fid, "field": name, "state": "unknown",
                "note": "这只标的还没有台账记录，未本轮取数",
                "source": None, "as_of": None, "fetched_at": None,
                "timezone": None, "period": None, "error": None,
                "market_time": None, "preview": None,
            }
            for fid, name, _contract, _src in FIELD_DEFS
        ]

    cov = coverage or {}
    src_rows = cov.get("sources") or []
    packets = {p.get("id"): p for p in _research_doc(day, ticker).get("packets", []) if isinstance(p, dict)}
    out: list[dict] = []

    for fid, name, contract, expect_src in FIELD_DEFS:
        meta = {
            "id": fid, "field": name, "state": "missing", "note": contract,
            "source": None, "as_of": None, "fetched_at": None,
            "timezone": None, "period": None, "error": None,
            "market_time": None, "preview": previews.get(fid),
        }
        if fid in _COVERAGE_DIRECT:
            fm = cov.get(fid)
            if isinstance(fm, dict):
                meta.update({
                    "state": fm.get("status") or "missing",
                    "source": fm.get("source"),
                    "as_of": fm.get("as_of"),
                    "fetched_at": fm.get("fetched_at"),
                    "timezone": fm.get("timezone"),
                    "period": fm.get("period"),
                    "market_time": fm.get("market_time"),
                    "error": fm.get("error"),
                })
            else:
                meta["error"] = "coverage.json 没有这个字段"
        elif fid == "earnings":
            es = cov.get("earnings_source")
            if isinstance(es, dict) and es.get("status"):
                meta.update({
                    "state": es.get("status"), "source": es.get("source"),
                    "as_of": es.get("as_of"), "fetched_at": es.get("fetched_at"),
                    "error": es.get("error"),
                })
            else:
                row = _from_sources(src_rows, "earnings")
                if row:
                    meta["state"] = _SOURCE_STATE.get(row.get("state"), "missing")
                    meta["source"] = row.get("id")
                    meta["error"] = row.get("note") or None
                    if meta["state"] == "available":
                        meta["error"] = None
                else:
                    meta["error"] = "未确认下一次财报日"
        elif fid in ("social", "events", "macro"):
            if fid == "macro" and ledger.get("macro"):
                meta["state"] = "available"
                meta["source"] = "supabase"
            else:
                row = _from_sources(src_rows, fid)
                if row:
                    meta["state"] = _SOURCE_STATE.get(row.get("state"), "missing")
                    meta["source"] = None if meta["state"] == "unsupported" else row.get("id")
                    meta["note"] = row.get("note") or contract
                    if meta["state"] == "missing":
                        meta["error"] = row.get("note") or None
                else:
                    meta["state"] = "unsupported" if fid == "social" else "missing"
        elif fid == "chain":
            if chain_meta:
                meta["state"] = "available"
                meta["source"] = chain_meta.get("source")
            else:
                meta["error"] = "没有链快照"
        elif fid == "account":
            acct = (ledger.get("risk") or {}).get("account_equity")
            if acct:
                meta["state"] = "available"
                meta["source"] = acct.get("source") or "futu"
                meta["fetched_at"] = acct.get("fetched_at")
            else:
                meta["error"] = "账户权益读不到"
        elif fid in ("business", "competition", "risk"):
            pkt = packets.get(fid)
            if pkt is None:
                meta["error"] = "研究包未找到该字段"
            elif pkt.get("status") == "ok":
                meta["state"] = "available"
                meta["source"] = expect_src
            else:
                meta["error"] = (pkt.get("text") or "")[:160] or f"研究包状态 {pkt.get('status')}"
        elif fid == "governance":
            meta["state"] = "unsupported"
        out.append(meta)
    return out
