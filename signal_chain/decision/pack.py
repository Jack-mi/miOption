"""证据摘要。只写已有字段，缺失的节标明缺失。"""

from __future__ import annotations

from ..data.models import MarketData


def _line(label: str, status: str, source: str | None, as_of, extra: str = "") -> str:
    when = as_of.isoformat() if as_of else "无时点"
    who = source or "无出处"
    tail = f" {extra}" if extra else ""
    return f"- {label}: {status}，出处 {who}，时点 {when}{tail}"


def render_pack(market: MarketData) -> str:
    snap = market.snapshot
    tech = []
    tech.append(_line("报价", snap.quote.meta.status, snap.quote.meta.source, snap.quote.meta.as_of,
                      f"最新价 {snap.quote.last}" if snap.quote.meta.status == "available" else ""))
    tech.append(_line("日线", snap.kline.meta.status, snap.kline.meta.source, snap.kline.meta.as_of,
                      f"{len(snap.kline.bars)} 根" if snap.kline.meta.status == "available" else ""))
    sma = snap.technical.indicators.get("sma_5")
    tech.append(_line(
        "均线", snap.technical.meta.status, snap.technical.meta.source, snap.technical.meta.as_of,
        f"sma_5 {sma}" if sma is not None and snap.technical.meta.status == "available" else "",
    ))

    if snap.capital_flow.status == "available" and market.flow_net is not None:
        flow = _line("净流入", "available", snap.capital_flow.source, snap.capital_flow.as_of,
                     f"净额 {market.flow_net}")
    else:
        flow = f"- 资金面缺失: {snap.capital_flow.error or snap.capital_flow.status}"

    parts = ["## 技术面", *tech, "", "## 资金面", flow, "", "## 基本面"]
    if snap.fundamentals.status == "available":
        parts.append(_line("财务", "available", snap.fundamentals.source, snap.fundamentals.as_of,
                           f"期间 {snap.fundamentals.period}"))
    else:
        parts.append(f"- 财务缺失: {snap.fundamentals.error or snap.fundamentals.status}")
    if market.facts:
        for fact in market.facts:
            parts.append(f"- 单源 {fact.metric}: {fact.value}，出处 {fact.source}，期间 {fact.period}")
    else:
        parts.append("- 单源营收缺失")
    if snap.earnings_date is not None:
        parts.append(f"- 财报日: {snap.earnings_date.isoformat()}，出处 {snap.earnings_source}")
    else:
        parts.append("- 财报日缺失")

    if market.ratios:
        for ratio in market.ratios:
            parts.append(
                f"- {ratio.metric}: available，出处 {ratio.source}，期间 {ratio.period}，值 {ratio.value}"
            )
    parts += ["", "## 新闻"]
    if snap.news.status == "available" and market.news_text:
        parts.append(_line("标题", "available", snap.news.source, snap.news.as_of, market.news_text))
    else:
        parts.append(f"- 新闻缺失: {snap.news.error or snap.news.status}")

    parts += ["", "## 社交"]
    if market.social:
        for item in market.social:
            parts.append(f"- {item.source}: {item.text}")
    else:
        parts.append("- 社交缺失")

    by_section = {item.section: item for item in market.excerpts}
    parts += ["", "## 商业模式"]
    if "business" in by_section:
        item = by_section["business"]
        when = item.as_of.isoformat() if item.as_of else "无时点"
        parts.append(f"- 正文: {item.text}，出处 {item.source}，时点 {when}")
    else:
        parts.append("- 商业模式缺失，没有生意描述字段。")
    parts += ["", "## 竞争"]
    if "competition" in by_section:
        item = by_section["competition"]
        when = item.as_of.isoformat() if item.as_of else "无时点"
        parts.append(f"- 正文: {item.text}，出处 {item.source}，时点 {when}")
    else:
        parts.append("- 竞争缺失，没有行业、对手、份额字段。")
    parts += ["", "## 风险"]
    risk_bits = [by_section[key] for key in ("risk_factors", "governance") if key in by_section]
    if risk_bits:
        for item in risk_bits:
            when = item.as_of.isoformat() if item.as_of else "无时点"
            parts.append(f"- {item.section}: {item.text}，出处 {item.source}，时点 {when}")
    else:
        parts.append("- 风险缺失，没有管理层、治理、监管字段。")
    parts += ["", "## 宏观"]
    if market.macro:
        for point in market.macro:
            parts.append(_line(point.series, "available", point.source, point.as_of, f"值 {point.value}"))
    else:
        parts.append("- 宏观缺失")
    return "\n".join(parts)
