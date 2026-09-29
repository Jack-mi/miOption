"""同一进程里的这一轮快照和决策记录。换标的或换交易日才重新取数。"""

from __future__ import annotations

from datetime import date, datetime, timezone

_markets: dict[tuple[str, str], object] = {}
_decisions: dict[tuple[str, str], object] = {}
_market_cached_at: dict[tuple[str, str], datetime] = {}


def key(ticker: str, trade_date: date) -> tuple[str, str]:
    return (ticker, trade_date.isoformat())


def get_market(ticker: str, trade_date: date):
    return _markets.get(key(ticker, trade_date))


def fresh_market(ticker: str, trade_date: date):
    cached = _market_cached_at.get(key(ticker, trade_date))
    if cached is None or (datetime.now(timezone.utc) - cached).total_seconds() > 60:
        return None
    return get_market(ticker, trade_date)


def put_market(ticker: str, trade_date: date, market) -> None:
    _markets[key(ticker, trade_date)] = market
    _market_cached_at[key(ticker, trade_date)] = datetime.now(timezone.utc)
    _decisions.pop(key(ticker, trade_date), None)


def get_decision(ticker: str, trade_date: date):
    decision = _decisions.get(key(ticker, trade_date))
    if decision is None or get_market(ticker, trade_date) is None:
        return None
    return decision


def put_decision(ticker: str, trade_date: date, decision) -> None:
    _decisions[key(ticker, trade_date)] = decision


def clear() -> None:
    _markets.clear()
    _decisions.clear()
    _market_cached_at.clear()
