"""Polymarket 只读。个股映射空着就跳过。宏观主题走公开客户端，不配 key。"""

from __future__ import annotations

import json
from pathlib import Path

MAP_PATH = Path(__file__).with_name("events.json")
TOPICS = ("fed", "recession", "cpi")
MIN_VOLUME = 10_000


def load_map(path: Path = MAP_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in data.items() if v}


def prices(payload: dict | list) -> list[tuple[str, float]]:
    event = payload[0] if isinstance(payload, list) and payload else payload
    if not isinstance(event, dict):
        return []
    markets = event.get("markets") or []
    out = []
    for market in markets:
        name = str(market.get("question") or market.get("groupItemTitle") or "").strip()
        raw = market.get("outcomePrices") or market.get("lastTradePrice")
        if isinstance(raw, str) and raw.startswith("["):
            try:
                raw = json.loads(raw)[0]
            except (json.JSONDecodeError, IndexError):
                raw = None
        try:
            price = float(raw)
        except (TypeError, ValueError):
            continue
        if name:
            out.append((name, price))
    return out[:3]


def _loads(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


def _market_row(event: dict, market: dict) -> dict | None:
    if market.get("closed"):
        return None
    prices = _loads(market.get("outcomePrices") or "[]")
    tokens = _loads(market.get("clobTokenIds") or "[]")
    try:
        prob = float(prices[0])
        volume = float(market.get("volume") or 0)
    except (TypeError, ValueError, IndexError):
        return None
    return {
        "event": str(event.get("title") or ""),
        "slug": str(event.get("slug") or ""),
        "question": str(market.get("question") or ""),
        "prob_yes": prob,
        "volume": volume,
        "neg_risk": bool(market.get("negRisk")),
        "token_id": str(tokens[0]) if tokens else "",
    }


def macro_odds(events: list) -> list[dict]:
    """活跃市场的 Yes 价。互斥组整组保留；其余成交量低于 1 万美元的丢掉。"""
    found: list[dict] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        rows = [row for market in (event.get("markets") or []) if (row := _market_row(event, market))]
        if not rows:
            continue
        if any(row["neg_risk"] for row in rows):
            if sum(row["volume"] for row in rows) < MIN_VOLUME:
                continue
            found.extend(rows)
        else:
            found.extend(row for row in rows if row["volume"] >= MIN_VOLUME)
    return sorted(found, key=lambda row: -row["volume"])


def system_https_proxy() -> str | None:
    """本机系统 HTTPS 代理。环境变量优先，否则读 macOS 的 scutil。"""
    import os
    import subprocess

    chosen = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if chosen:
        return chosen
    try:
        text = subprocess.check_output(["scutil", "--proxy"], text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return None
    enabled = host = port = None
    for line in text.splitlines():
        item = line.strip()
        if item.startswith("HTTPSEnable"):
            enabled = item.rsplit(" ", 1)[-1] == "1"
        elif item.startswith("HTTPSProxy"):
            host = item.split(":", 1)[-1].strip()
        elif item.startswith("HTTPSPort"):
            port = item.split(":", 1)[-1].strip()
    if enabled and host and port:
        return f"http://{host}:{port}"
    return None


def _use_proxy(client, proxy: str) -> None:
    import httpx

    for name in ("gamma", "data", "clob", "rfq"):
        transport = getattr(client._ctx, name)
        transport._client.close()
        transport._client = httpx.Client(
            base_url=transport._base_url,
            proxy=proxy,
            timeout=httpx.Timeout(connect=10.0, read=20.0, write=10.0, pool=5.0),
            http2=False,
        )


def fetch_macro_events(topics: tuple[str, ...] = TOPICS) -> list[dict]:
    """PublicClient 拉公开事件。不传私钥，不建交易客户端。"""
    from polymarket import PublicClient

    proxy = system_https_proxy()
    events: list[dict] = []
    with PublicClient() as client:
        if proxy:
            _use_proxy(client, proxy)
        for topic in topics:
            page = client.list_events(tag_slug=topic, closed=False, page_size=20).first_page()
            for event in page.items:
                events.append(_event_dict(event))
    return events


def _event_dict(event) -> dict:
    markets = []
    for market in event.markets or []:
        yes = market.outcomes.yes if market.outcomes else None
        state = market.state
        metrics = market.metrics
        markets.append({
            "question": market.question,
            "closed": bool(state and state.closed),
            "negRisk": bool(state and state.neg_risk),
            "outcomePrices": [yes.price if yes and yes.price is not None else None],
            "clobTokenIds": [str(yes.token_id) if yes and yes.token_id else ""],
            "volume": float(metrics.volume or 0) if metrics else 0,
        })
    return {"title": event.title, "slug": event.slug, "markets": markets}
