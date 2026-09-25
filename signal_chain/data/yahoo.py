"""Yahoo 是多处兜底。解析与 yfinance 调用分开，测试不访问公网。"""

from __future__ import annotations


def revenue_from_info(info: dict) -> float | None:
    try:
        value = float(info.get("totalRevenue"))
    except (TypeError, ValueError):
        return None
    if value != value:
        return None
    return value


def named_float(info: dict, key: str) -> float | None:
    try:
        value = float((info or {}).get(key))
    except (TypeError, ValueError):
        return None
    if value != value:
        return None
    return value


def headlines(items: list, limit: int = 3) -> str | None:
    titles = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        content = item.get("content")
        if not title and isinstance(content, dict):
            title = content.get("title")
        title = str(title or "").strip()
        if title:
            titles.append(title)
        if len(titles) >= limit:
            break
    return "；".join(titles) or None
