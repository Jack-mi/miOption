"""结构化中文简报生成器。

按固定大纲用台账数据确定性生成正文：全中文、简洁、无英文报错堆砌。
原始 reporter 文件仍在 reports/{date}/{ticker}.md，本生成器不改写它，
只是给 web 一份可读的正文。大纲六段，顺序固定：

一、决策动作 / 二、数据状态 / 三、合成结论
四、三份信号 / 五、候选结构 / 六、结构菜单摘要与复核限制
"""

from __future__ import annotations

_DIR_ZH = {
    "strong_buy": "强烈看多", "buy": "看多", "neutral": "中性",
    "sell": "看空", "strong_sell": "强烈看空",
}
_AGREE_ZH = {
    "aligned": "互相印证", "partial": "部分一致", "conflicted": "方向分歧",
    "single_source": "单源", "insufficient_data": "数据不足",
}
_STATUS_ZH = {
    "actionable": "可行动", "opinion": "观点", "insufficient_data": "数据不足",
}
_ENGINE_ZH = {"trend": "走势（确定性规则）", "research": "研究（模型）", "value": "价值（财务流程 + 模型）"}

# 英文噪声标记：出现即截断，不把报错堆进简报
_NOISE = ("ERROR", "Using SOCKS", "Before calling", "please subscribe", "pip install",
          "socksio", "Get Real-time", "Traceback", "http")


def _clean(text: str, limit: int = 90) -> str:
    """清洗一段台账文本：去掉英文报错尾巴，统一中文 missing 说法。"""
    if not text:
        return ""
    for marker in _NOISE:
        idx = text.find(marker)
        if idx > 0:
            text = text[:idx]
    text = text.replace(" missing", "缺失").replace("missing", "缺失").replace("；降级: 无日线", "").replace("；降级：无日线", "")
    text = text.replace("trend:", "走势：").replace("research:", "研究：").replace("value:", "价值：")
    text = text.replace(" | ", "；").replace("弃权 走势：", "走势弃权：").replace("弃权 研究：", "研究弃权：").replace("弃权 价值：", "价值弃权：")
    text = text.replace("： ", "：")
    text = text.strip("；;：: ，,。")
    if len(text) > limit:
        text = text[:limit].rstrip("，,；; ") + "…"
    return text


def _fmt_big(text: str) -> str:
    """长串数字转「万」：净流出 -27417840.0 → 净流出 -2,741.8 万。"""
    import re

    def conv(m):
        v = float(m.group(0))
        if abs(v) >= 10000:
            return f"{v / 10000:,.1f} 万"
        return f"{v:,.0f}"

    return re.sub(r"-?\d{5,}(?:\.\d+)?", conv, text)


def _fmt_money(v: float | None) -> str:
    if v is None:
        return "—"
    if abs(v) >= 10000:
        return f"{v / 10000:,.1f} 万"
    return f"{v:,.0f}"


def _signed(v: float, d: int = 2) -> str:
    return f"{'+' if v > 0 else ''}{v:.{d}f}"


def build_report(console: dict) -> str:
    """console 聚合 dict → 中文 markdown 正文。"""
    ticker = console["ticker"]
    as_of = console.get("asOf") or "—"
    quote = console.get("quote") or {}
    ens = console.get("ensemble") or {}
    signals = console.get("signals") or {}
    risk = console.get("risk") or {}
    gate = risk.get("signal_gate") or {}
    account = risk.get("account_equity") or {}
    menu = console.get("menu") or []
    cards = console.get("cards") or []
    chain = console.get("chain")
    sources = console.get("sources") or []

    lines: list[str] = []
    lines.append(f"# {ticker} 期权决策简报（{as_of}）")
    lines.append("")

    # 一、决策动作
    decision = risk.get("decision") or ("观望" if not gate.get("approved") else "关注")
    lines.append("## 一、决策动作")
    lines.append("")
    lines.append(f"**{decision}。** 这条链路只读，不下单。")
    lines.append("")

    # 二、数据状态
    counts = {"available": 0, "missing": 0, "unsupported": 0, "stale": 0}
    for s in sources:
        if s.get("state") in counts:
            counts[s["state"]] += 1
    lines.append("## 二、数据状态")
    lines.append("")
    if quote.get("spot") is not None and quote.get("status") == "available":
        lines.append(f"- 报价：**可用**（{quote.get('source') or 'futu'}，"
                     f"{quote['spot']} {console.get('currency', 'USD')}，"
                     f"市场时间 {quote.get('market_time') or '—'}）")
    else:
        lines.append("- 报价：**缺失**（非可用报价不携带价格）")
    if chain:
        lines.append(f"- 期权链：{chain.get('source')} {chain.get('rows')} 行"
                     f"（{'已降级' if chain.get('degraded') else '未降级'}）")
    else:
        lines.append("- 期权链：**缺失**")
    if account:
        lines.append(f"- 账户：{account.get('env', '—')}/{account.get('currency', '—')}，"
                     f"权益 {_fmt_money(account.get('value'))}，"
                     f"可用现金 {_fmt_money(account.get('available_cash'))}")
    else:
        lines.append("- 账户：**读不到**（亏损上限检查已跳过）")
    lines.append(f"- 财报日：{console.get('earningsDate') or '未确认'}")
    lines.append(f"- 字段覆盖：可用 {counts['available']} · 缺失 {counts['missing']} · "
                 f"不支持 {counts['unsupported']}" + (f" · 过期 {counts['stale']}" if counts["stale"] else ""))
    lines.append("")

    # 三、合成结论
    direction = _DIR_ZH.get(ens.get("direction"), "中性")
    agreement = _AGREE_ZH.get(ens.get("agreement"), "数据不足")
    conviction = ens.get("conviction") or 0.0
    stop = ens.get("agreement") in ("conflicted", "insufficient_data")
    lines.append("## 三、合成结论")
    lines.append("")
    lines.append(f"方向：**{direction}**（{_signed(conviction, 4)}） · 一致性：**{agreement}**"
                 + ("　■" if stop else ""))
    notes = _clean(ens.get("quality_notes") or "", 160)
    if notes:
        lines.append("")
        lines.append(f"说明：{notes}。")
    lines.append("")

    # 四、三份信号
    lines.append("## 四、三份信号")
    lines.append("")
    for engine in ("trend", "research", "value"):
        s = signals.get(engine) or {}
        label = _ENGINE_ZH[engine]
        abstain = s.get("data_status") == "insufficient_data"
        if s.get("data_status") == "unknown":
            lines.append(f"- **{label}**：无记录（台账里没有这只标的）")
        elif abstain:
            gaps = "；".join(filter(None, (_clean(g, 40) for g in (s.get("data_gaps") or []))))
            lines.append(f"- **{label}**：弃权（数据不足）—— {gaps or '关键数据缺失'}，整票不投票")
        else:
            d = _DIR_ZH.get(s.get("direction"), "中性")
            c = s.get("conviction") or 0.0
            st = _STATUS_ZH.get(s.get("data_status"), "可行动")
            faces = _fmt_big(_clean(s.get("faces") or "", 60))
            tail = f"　依据：{faces}" if faces else ""
            lines.append(f"- **{label}**：{d}（{_signed(c)}） · {st}{tail}")
    lines.append("")

    # 五、候选结构
    lines.append("## 五、候选结构")
    lines.append("")
    if not gate.get("approved"):
        vetoes = "；".join(filter(None, (_clean(v, 60) for v in (gate.get("vetoes") or []))))
        lines.append(f"信号闸未过：{vetoes or '未通过'}。本轮不生成可过闸的交易结构。")
    elif cards:
        for c in cards[:5]:
            legs = f"卖 {c['short']['code']} / 买 {c['long']['code']}"
            ror = c.get("return_on_risk")
            ror_text = f"{ror * 100:.1f}%" if ror is not None else "—"
            lines.append(f"- **{c['name']}**（{c['tier']}）：{legs}，"
                         f"credit {c.get('credit')}，最大亏损 {c.get('max_loss')}，收益/风险 {ror_text}")
    else:
        lines.append("无候选结构：链上凑不出同时满足持仓量、价差与盈亏比门槛的双边合约。")
    lines.append("")

    # 六、结构菜单摘要 + 复核限制
    fit = sum(1 for m in menu if m.get("status") == "fit")
    unfit = sum(1 for m in menu if m.get("status") == "unfit")
    impossible = sum(1 for m in menu if m.get("status") == "impossible")
    review = risk.get("review") or {}
    lines.append("## 六、结构菜单摘要与复核")
    lines.append("")
    lines.append(f"结构菜单：适合 {fit} 项 · 不适合 {unfit} 项 · 做不了 {impossible} 项"
                 f"（完整 {len(menu)} 项见「期权链与结构」）。")
    findings = review.get("findings") or []
    if review.get("ok") and not findings:
        lines.append("复核：完成既定机械检查（非交易保证）。")
    else:
        cleaned = "；".join(filter(None, (_clean(f, 60) for f in findings))) or "复核未通过"
        lines.append(f"复核：{cleaned}。")
    lines.append("")
    lines.append("---")
    lines.append("本简报由台账数据确定性生成，只读，不构成交易建议；模型的影响力止于信号。")
    return "\n".join(lines)
