"""Reddit 社交。有官方凭据走官方接口；没有则解析 Arctic Shift 档案。"""

from __future__ import annotations

from datetime import date, datetime, timezone

_ARCHIVE_DAYS = 14


def titles(payload: dict, limit: int = 3) -> list[str]:
    children = ((payload.get("data") or {}).get("children")) or []
    out = []
    for child in children:
        title = str(((child.get("data") or {}).get("title")) or "").strip()
        if title:
            out.append(title)
        if len(out) >= limit:
            break
    return out


def archive_posts(payload: dict, trade_date: date, limit: int = 3) -> tuple[list[str], str]:
    """返回 (标题, used|stale|missing)。超过 14 天的档案不当作当前社交。"""
    rows = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows:
        return [], "missing"
    fresh: list[str] = []
    newest: date | None = None
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            posted = datetime.fromtimestamp(int(row.get("created_utc")), timezone.utc).date()
        except (TypeError, ValueError, OSError):
            continue
        if newest is None or posted > newest:
            newest = posted
        title = str(row.get("title") or "").strip()
        if title and (trade_date - posted).days <= _ARCHIVE_DAYS:
            fresh.append(title)
        if len(fresh) >= limit:
            break
    if fresh:
        return fresh[:limit], "used"
    if newest is not None:
        return [], "stale"
    return [], "missing"
