"""这一轮标的的上下文。只读已经取好的快照，不重新发请求。"""

from __future__ import annotations

from ..data.models import MarketData

_NAMES = (
    "quote", "kline", "sma", "flow", "chain",
    "fundamentals", "earnings", "filing",
    "business", "competition", "risk", "governance",
    "news", "social", "events",
    "macro",
)


def card(market: MarketData) -> str:
    snap = market.snapshot
    lines = [
        f"标的 {snap.ticker}，这场交易 {snap.as_of.isoformat()}。",
        f"盘面：{_face(snap.quote.meta.status, snap.as_of.isoformat())}",
        f"财报：{_face(snap.fundamentals.status, snap.fundamentals.period or '无期间')}",
        f"消息：{_face(snap.news.status, snap.news.as_of.isoformat() if snap.news.as_of else '无时点')}",
        f"宏观：{_macro_clock(market)}",
    ]
    return "\n".join(lines)


_FIELDS = {
    "quote": ("quote",),
    "kline": ("kline",),
    "sma": ("technical",),
    "flow": ("capital_flow",),
    "chain": ("chain",),
    "fundamentals": ("fundamentals",),
    "earnings": ("earnings",),
    "filing": ("earnings",),
    "business": ("earnings",),
    "competition": ("earnings",),
    "risk": ("risk_factors", "earnings"),
    "governance": ("earnings",),
    "news": ("news",),
    "social": ("social",),
    "events": ("events", "macro_odds"),
    "macro": ("macro",),
}


def slice(market: MarketData, name: str) -> str:
    if name not in _NAMES:
        return f"{name}缺失：没有这个切片"
    return f"{_SLICES[name](market)}\n{_provenance(market, name)}"


def _provenance(market: MarketData, name: str) -> str:
    fields = _FIELDS[name]
    rows = [row for row in market.sources if row.field in fields]
    if not rows:
        return "取数记录缺失"
    lines = ["取数"]
    for row in rows:
        note = f" {row.note}" if row.note else ""
        lines.append(f"{row.id} {row.state}{note}")
    return "\n".join(lines)


def _face(status: str, clock: str) -> str:
    if status == "available":
        return f"可用，时点 {clock}"
    return f"缺失，{status}"


def _macro_clock(market: MarketData) -> str:
    if not market.macro:
        return "缺失"
    latest = max(market.macro, key=lambda point: point.as_of)
    return f"可用，时点 {latest.as_of.isoformat()}"


def _quote(market: MarketData) -> str:
    snap = market.snapshot
    meta = snap.quote.meta
    if meta.status != "available" or snap.quote.last is None:
        return f"报价缺失：{meta.error or meta.status}"
    return f"报价：{snap.quote.last}，出处 {meta.source or '无出处'}，时点 {meta.as_of}"


def _kline(market: MarketData) -> str:
    snap = market.snapshot
    meta = snap.kline.meta
    if meta.status != "available" or not snap.kline.bars:
        return f"日线缺失：{meta.error or meta.status}"
    return f"日线：{len(snap.kline.bars)} 根，出处 {meta.source or '无出处'}，时点 {meta.as_of}"


def _sma(market: MarketData) -> str:
    snap = market.snapshot
    meta = snap.technical.meta
    sma = snap.technical.indicators.get("sma_5")
    if meta.status != "available" or sma is None:
        return f"均线缺失：{meta.error or meta.status}"
    return f"均线：sma_5 {sma}，出处 {meta.source or '无出处'}，时点 {meta.as_of}"


def _flow(market: MarketData) -> str:
    snap = market.snapshot
    meta = snap.capital_flow
    if meta.status != "available" or market.flow_net is None:
        return f"资金面缺失: {meta.error or meta.status}"
    return f"净流入：available，出处 {meta.source or '无出处'}，时点 {meta.as_of}，净额 {market.flow_net}"


def _chain(market: MarketData) -> str:
    chain = market.chain
    if chain is None or not chain.rows:
        return f"期权链缺失：{market.chain_error or '没有链'}"
    expiries = chain.expiries()
    return (
        f"期权链：{len(chain.rows)} 张，{len(expiries)} 个到期，现价 {chain.spot}，"
        f"出处 {chain.source}"
    )


def _fundamentals(market: MarketData) -> str:
    snap = market.snapshot
    fund = snap.fundamentals
    if fund.status != "available":
        return f"财报缺失: {fund.error or fund.status}"
    lines = [f"财报: available，出处 {fund.source or '无出处'}，期间 {fund.period or '无期间'}"]
    for fact in market.facts:
        filed = f"，申报 {fact.filed}" if fact.filed else ""
        lines.append(f"- {fact.metric}: {fact.value}，出处 {fact.source}，期间 {fact.period}{filed}")
    for ratio in market.ratios:
        lines.append(f"- {ratio.metric}: {ratio.value}，出处 {ratio.source}，期间 {ratio.period}")
    return "\n".join(lines)


def _earnings(market: MarketData) -> str:
    snap = market.snapshot
    if snap.earnings_date is None:
        return "财报日缺失"
    note = next(
        (
            row.note for row in market.sources
            if row.field == "earnings" and row.state == "used" and row.note
        ),
        "",
    )
    tail = f" {note}" if note else ""
    return f"财报日: {snap.earnings_date.isoformat()}，出处 {snap.earnings_source}{tail}"


def _filing(market: MarketData) -> str:
    note = next(
        (
            row.note for row in market.sources
            if row.field == "filing" and row.state == "used" and row.note
        ),
        "",
    )
    if not note:
        return "最近申报日缺失"
    source = next((row.id for row in market.sources if row.field == "filing" and row.state == "used"), "未知")
    if source == "futu_morningstar":
        return f"研究更新：{note}，出处 {source}"
    return f"最近申报日：{note}，出处 {source}"


def _excerpt(market: MarketData, section: str, missing: str) -> str:
    item = next((row for row in market.excerpts if row.section == section), None)
    if item is None or not item.text:
        return missing
    when = item.as_of.isoformat() if item.as_of else "无时点"
    flag = f"，{item.quality}" if item.quality else ""
    return f"{item.text}，出处 {item.source}，时点 {when}{flag}"


def _business(market: MarketData) -> str:
    body = _excerpt(market, "business", "商业模式缺失，没有生意描述字段。商业模式：缺失，没有对应字段。")
    if body.startswith("商业模式"):
        return body
    return f"商业模式：{body}"


def _competition(market: MarketData) -> str:
    return _excerpt(market, "competition", "竞争缺失，没有行业、对手、份额字段。竞争：缺失，没有对应字段。")


def _risk(market: MarketData) -> str:
    item = next((row for row in market.excerpts if row.section == "risk_factors"), None)
    if item is None or not item.text:
        return "风险缺失，没有管理层、治理、监管字段。风险：缺失，没有对应字段。"
    when = item.as_of.isoformat() if item.as_of else "无时点"
    flag = f"，{item.quality}" if item.quality else ""
    return f"risk_factors: {item.text}，出处 {item.source}，时点 {when}{flag}"


def _governance(market: MarketData) -> str:
    item = next((row for row in market.excerpts if row.section == "governance"), None)
    if item is None or not item.text:
        return "治理缺失"
    if _toc(item.text):
        return "治理缺失：目录不当成正文"
    when = item.as_of.isoformat() if item.as_of else "无时点"
    return f"governance: {item.text}，出处 {item.source}，时点 {when}"


def _toc(text: str) -> bool:
    import re
    return len(re.findall(r"\d{1,3}\s+[A-Z]", text)) >= 4


def _news(market: MarketData) -> str:
    snap = market.snapshot
    if snap.news.status != "available" or not market.news_text:
        return f"新闻缺失: {snap.news.error or snap.news.status}"
    when = snap.news.as_of.isoformat() if snap.news.as_of else "无时点"
    return f"标题: available，出处 {snap.news.source or '无出处'}，时点 {when} {market.news_text}"


def _social(market: MarketData) -> str:
    if not market.social:
        note = next((row.note for row in market.sources if row.field == "social" and row.note), "没有帖子")
        return f"社交缺失：{note}"
    return "\n".join(f"社交：{item.source}: {item.text}" for item in market.social)


def _events(market: MarketData) -> str:
    if not market.events:
        note = next(
            (row.note for row in market.sources if row.field == "macro_odds" and row.state == "missing" and row.note),
            "",
        )
        if not note:
            note = next((row.note for row in market.sources if row.field == "events" and row.note), "没有事件")
        return f"事件赔率缺失：{note}"
    return "\n".join(
        f"事件：{item.slug} {item.outcome} {item.price}" for item in market.events
    )


def _macro(market: MarketData) -> str:
    if not market.macro:
        return "宏观缺失"
    lines = []
    for point in market.macro:
        lines.append(
            f"{point.series}: available，出处 {point.source}，时点 {point.as_of.isoformat()} 值 {point.value}"
        )
    return "\n".join(lines)


_SLICES = {
    "quote": _quote,
    "kline": _kline,
    "sma": _sma,
    "flow": _flow,
    "chain": _chain,
    "fundamentals": _fundamentals,
    "earnings": _earnings,
    "filing": _filing,
    "business": _business,
    "competition": _competition,
    "risk": _risk,
    "governance": _governance,
    "news": _news,
    "social": _social,
    "events": _events,
    "macro": _macro,
}
