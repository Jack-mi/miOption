"""主 Agent 点名顺序：先取数，再研究决策，再 review。hook 在执行前拒绝。"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from ..config import parse_ticker
from . import session


def deny_reason(tool_name: str, tool_input: dict | None, *, today: date | None = None) -> str | None:
    name = tool_name or ""
    tool_input = tool_input or {}
    watched = ("data_agent", "decision_agent", "review_agent")
    if not any(marker in name for marker in watched):
        return None
    if "review_agent" in name and tool_input.get("load"):
        return "review 不能取数"
    ticker = str(tool_input.get("ticker") or "")
    if ticker:
        parsed = parse_ticker(ticker)
        if parsed.market != "US":
            return "只覆盖美股"
        day = today or datetime.now(ZoneInfo("America/New_York")).date()
        canonical = parsed.canonical
        if "decision_agent" in name and session.fresh_market(canonical, day) is None:
            return "没有快照"
        if "review_agent" in name and session.get_decision(canonical, day) is None:
            return "没有决策记录"
    elif "decision_agent" in name:
        return "没有快照"
    elif "review_agent" in name:
        return "没有决策记录"
    return None
