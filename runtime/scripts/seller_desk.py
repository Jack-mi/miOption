#!/usr/bin/env python3
"""Seller-desk CLI: scan / list / verdict / monitor. No OSM API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mioption_runtime.seller.desk import SellerDesk  # noqa: E402
from mioption_runtime.seller.scan import DEFAULT_WATCHLIST  # noqa: E402


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, default=str))


def main() -> int:
    p = argparse.ArgumentParser(description="Local seller desk (OpenD). Does not call osmtrade.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("scan", help="Scan watchlist into local cards")
    sp.add_argument("--underlyings", default=",".join(DEFAULT_WATCHLIST))

    sl = sub.add_parser("list", help="List saved cards")
    sl.add_argument("--status", default="")

    sv = sub.add_parser("verdict", help="adopt/watch/reject (no order)")
    sv.add_argument("card_id")
    sv.add_argument("verdict", choices=["adopt", "watch", "reject"])
    sv.add_argument("--note", default="")

    sub.add_parser("monitor", help="Mark tracked cards; remind-only")

    args = p.parse_args()
    desk = SellerDesk()
    if args.cmd == "scan":
        names = [x.strip() for x in args.underlyings.split(",") if x.strip()]
        _print(desk.scan(names))
        return 0
    if args.cmd == "list":
        _print(desk.list_cards(status=args.status or None))
        return 0
    if args.cmd == "verdict":
        _print(desk.verdict(args.card_id, args.verdict, note=args.note))
        return 0
    if args.cmd == "monitor":
        _print(desk.monitor_tick())
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
