"""Refresh slow research evidence only; no quote, chain, account, or order calls."""

from __future__ import annotations

import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

from ..config import load_settings, parse_ticker
from .layer import load


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", help="Comma-separated US symbols; defaults to watchlist")
    args = parser.parse_args()
    settings = load_settings()
    tickers = args.tickers.split(",") if args.tickers else settings.watchlist
    day = datetime.now(ZoneInfo("America/New_York")).date()
    failures = []
    for symbol in tickers:
        ticker = parse_ticker(symbol)
        if ticker.market != "US":
            failures.append(f"{ticker.canonical}: unsupported market")
            continue
        try:
            market = load(ticker, day, settings, slow_only=True)
            print(ticker.canonical, "persisted=" + str(market.evidence_persisted),
                  "fundamentals=" + market.snapshot.fundamentals.status,
                  "earnings=" + str(market.snapshot.earnings_date))
            if not market.evidence_persisted:
                failures.append(ticker.canonical + ": evidence not persisted")
        except Exception as exc:
            failures.append(ticker.canonical + ": " + str(exc)[:120])
    if failures:
        raise SystemExit("\n".join(failures))


if __name__ == "__main__":
    main()
