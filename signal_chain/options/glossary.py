"""27 个结构的一句说明，来自策略笔记。只解释，不改菜单结论。"""

from __future__ import annotations

from ..config import REPO_ROOT

_NOTES = {
    "买入看涨": "Long Call.md",
    "买入看跌": "Long Put.md",
    "裸卖看涨": "Naked Call (Uncovered Call, Short Call).md",
    "裸卖看跌": "Naked Put (Uncovered Put, Short Put).md",
    "保护性认沽": "Protective Put (Married Put).md",
    "牛市看涨价差": "Bull Call Spread (Debit Call Spread).md",
    "牛市认沽价差": "Bull Put Spread (Credit Put Spread).md",
    "熊市看涨价差": "Bear Call Spread (Credit Call Spread).md",
    "熊市认沽价差": "Bear Put Spread.md",
    "备兑看涨": "Covered Call (Buy-Write).md",
    "现金担保认沽": "Cash-Secured Put.md",
    "领口": "Collar (Protective Collar).md",
    "买入跨式": "Long Straddle.md",
    "卖出跨式": "Short Straddle.md",
    "买入宽跨": "Long Strangle (Long Combination).md",
    "卖出宽跨": "Short Strangle.md",
    "带式": "Strap.md",
    "条式": "Strip.md",
    "认购日历价差": "Long Call Calendar Spread.md",
    "认沽日历价差": "Long Put Calendar Spread.md",
    "对角认购价差": "Diagonal Call Spread.md",
    "买入认购蝶式": "Long Call Butterfly.md",
    "买入认沽蝶式": "Long Put Butterfly.md",
    "买入认购鹰式": "Long Call Condor.md",
    "买入认沽鹰式": "Long Put Condor.md",
    "卖出铁蝶": "Short Iron Butterfly.md",
    "卖出铁鹰": "Short Condor (Iron Condor).md",
}

_DIR = REPO_ROOT / "knowledge" / "wiki" / "strategies"


def strategy_blurb(name: str) -> str:
    filename = _NOTES.get(name)
    if not filename:
        return ""
    path = _DIR / filename
    if not path.exists():
        return ""
    return _first_sentence(path.read_text(encoding="utf-8"))


def _first_sentence(text: str) -> str:
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end >= 0:
            body = text[end + 4:]
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-") or line.startswith("["):
            continue
        return line
    return ""
