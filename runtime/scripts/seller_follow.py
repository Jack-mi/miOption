#!/usr/bin/env python3
"""Follow local seller cards. Default dry-run. Does not call OSM.

Futu SIMULATE does not support combo option orders. Default submit without
--legs sequential only marks research_open. Sequential per-leg place is opt-in.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mioption_runtime.futu.policy import TradePolicy  # noqa: E402
from mioption_runtime.futu.trade import get_trade_backend  # noqa: E402
from mioption_runtime.seller.follow import follow_once, stop_path  # noqa: E402
from mioption_runtime.seller.scan import DEFAULT_WATCHLIST  # noqa: E402
from mioption_runtime.seller.store import SellerStore, default_root  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(
        description=(
            "Follow adopted local cards. Dry-run unless --submit. "
            "Touch STOP in the seller data dir to halt. No osmtrade API."
        )
    )
    p.add_argument("--submit", action="store_true", help="Leave dry-run; still no combo")
    p.add_argument(
        "--legs",
        choices=["none", "sequential"],
        default="none",
        help="sequential = per-leg SIMULATE place (instant naked-leg risk)",
    )
    p.add_argument("--whitelist", default=",".join(DEFAULT_WATCHLIST))
    args = p.parse_args()
    store = SellerStore(default_root())
    policy = TradePolicy()
    trade = get_trade_backend(policy=policy) if args.submit and args.legs == "sequential" else None
    names = [x.strip() for x in args.whitelist.split(",") if x.strip()]
    payload = follow_once(
        store,
        trade=trade,
        policy=policy,
        submit=args.submit,
        sequential=args.legs == "sequential",
        whitelist=names,
    )
    payload["stop_file"] = str(stop_path(store))
    print(json.dumps(payload, indent=2, default=str))
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
