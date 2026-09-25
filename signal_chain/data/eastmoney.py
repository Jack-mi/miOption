"""东方财富公开 HTTP。港股资金流兜底和港股财务第二源。不引入 AkShare。"""

from __future__ import annotations


def hk_secid(code: str) -> str:
    return f"116.{code.zfill(5)}"


def net_inflow(payload: dict) -> tuple[str, float] | None:
    """k 线第二列按该接口的主力净流入读。形状不对就放弃，不拿成交额顶上。"""
    klines = ((payload.get("data") or {}).get("klines")) or []
    if not klines:
        return None
    parts = str(klines[-1]).split(",")
    if len(parts) < 2:
        return None
    day, raw = parts[0][:10], parts[1]
    try:
        value = float(raw)
    except ValueError:
        return None
    if len(day) < 10:
        return None
    return day, value


def revenue(payload: dict) -> tuple[float, str] | None:
    rows = ((payload.get("result") or {}).get("data")) or []
    if not rows or not isinstance(rows[0], dict):
        return None
    row = rows[0]
    period = str(row.get("REPORT_DATE") or "")[:10]
    try:
        value = float(row.get("OPERATE_INCOME"))
    except (TypeError, ValueError):
        return None
    if not period[:4].isdigit():
        return None
    return value, f"FY{period[:4]}"
