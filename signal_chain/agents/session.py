"""同一进程里的这一轮快照和决策记录。换标的或换交易日才重新取数。"""

from __future__ import annotations

from datetime import date

_markets: dict[tuple[str, str], object] = {}
_decisions: dict[tuple[str, str], object] = {}


def key(ticker: str, trade_date: date) -> tuple[str, str]:
    return (ticker, trade_date.isoformat())


def get_market(ticker: str, trade_date: date):
    return _markets.get(key(ticker, trade_date))


def put_market(ticker: str, trade_date: date, market) -> None:
    _markets[key(ticker, trade_date)] = market


def get_decision(ticker: str, trade_date: date):
    return _decisions.get(key(ticker, trade_date))


def put_decision(ticker: str, trade_date: date, decision) -> None:
    _decisions[key(ticker, trade_date)] = decision


def clear() -> None:
    _markets.clear()
    _decisions.clear()
