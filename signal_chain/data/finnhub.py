"""Finnhub 公司新闻。"""

from __future__ import annotations

from datetime import date, timedelta


def news_url(symbol: str, session: date, token: str) -> str:
    start = session - timedelta(days=7)
    return (
        "https://finnhub.io/api/v1/company-news"
        f"?symbol={symbol}&from={start.isoformat()}&to={session.isoformat()}&token={token}"
    )


def headlines(payload, limit: int = 3) -> str | None:
    rows = payload if isinstance(payload, list) else []
    titles = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        title = str(item.get("headline") or "").strip()
        if title:
            titles.append(title)
        if len(titles) >= limit:
            break
    return "；".join(titles) or None


def public_error(exc: BaseException) -> str:
    import re
    text = re.sub(r"token=[^&\s'\"]+", "token=***", str(exc))
    return text[:160]
