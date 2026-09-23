"""DSA 产物适配：report_YYYYMMDD.md 中目标标的段落 -> RawBundle。

映射（方案锁定）：
操作 买入/观望/卖出 -> BUY/NEUTRAL/SELL；评分 -> conviction=(score-50)/50；
score>=85 且买入 -> STRONG_BUY；score<=15 且卖出 -> STRONG_SELL。
段落定位是宽容式正则，M0 拿到真实报告后固化进契约测试。
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from ..config import NormTicker
from ..schema import Direction
from .base import RawBundle

_ACTION_MAP = {
    "买入": Direction.BUY,
    "观望": Direction.NEUTRAL,
    "卖出": Direction.SELL,
}


def _extract_section(report_text: str, t: NormTicker) -> str | None:
    """按 markdown 标题切块，返回包含标的代码/名称的最长相关块。"""
    blocks = re.split(r"(?m)^(#{1,3}\s.*)$", report_text)
    digits = t.code.lstrip("0") or "0"
    candidates: list[str] = []
    for i in range(1, len(blocks), 2):
        header = blocks[i]
        body = blocks[i + 1] if i + 1 < len(blocks) else ""
        chunk = header + body
        if digits in chunk or t.code in chunk or t.dsa_format.lower() in chunk.lower():
            candidates.append(chunk)
    if not candidates:
        return None
    return max(candidates, key=len).strip()


def _extract_score(text: str) -> float | None:
    m = re.search(r"评分[：:\s]*(\d{1,3})", text)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d{1,3})\s*/\s*100", text)
    return float(m.group(1)) if m else None


def _extract_action(text: str) -> Direction | None:
    for word, direction in _ACTION_MAP.items():
        if word in text:
            return direction
    return None


class DsaAdapter:
    engine = "dsa"

    def __init__(self, data_sources: list[str] | None = None):
        self.data_sources = data_sources or ["akshare", "yfinance", "futu"]

    def load(self, report_path: Path, t: NormTicker, as_of: date,
             llm_model: str | None = None) -> RawBundle:
        text = report_path.read_text(encoding="utf-8")
        section = _extract_section(text, t)

        direction: Direction | None = None
        conviction = 0.0
        meta: dict = {}
        if section:
            score = _extract_score(section)
            action = _extract_action(section)
            meta["score"] = score
            if score is not None:
                conviction = max(-1.0, min(1.0, (score - 50) / 50))
            if action is not None and score is not None:
                if action == Direction.BUY and score >= 85:
                    direction = Direction.STRONG_BUY
                elif action == Direction.SELL and score <= 15:
                    direction = Direction.STRONG_SELL
                else:
                    direction = action
            elif action is not None:
                direction = action

        return RawBundle(
            engine=self.engine,
            ticker=t.canonical,
            market=t.market,
            as_of=as_of,
            report_ref=str(report_path),
            direction=direction,
            conviction=round(conviction, 4),
            data_sources=list(self.data_sources),
            llm_model=llm_model,
            texts={"report_section": section or ""},
            meta=meta,
        )
