"""StockTwits 社交兜底。公开接口，按小时限额在调用方间隔。"""

from __future__ import annotations

import time

_LAST = 0.0
_GAP = 18.0  # 200 次/小时


def wait_turn(now=time.monotonic, sleep=time.sleep) -> None:
    global _LAST
    gap = now() - _LAST
    if _LAST and gap < _GAP:
        sleep(_GAP - gap)
    _LAST = now()


def titles(payload: dict, limit: int = 3) -> list[str]:
    out = []
    for message in payload.get("messages") or []:
        body = str(message.get("body") or "").strip()
        if body:
            out.append(body[:160])
        if len(out) >= limit:
            break
    return out
