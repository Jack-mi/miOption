#!/usr/bin/env python3
"""Follow local seller cards in research-only mode; never place an order."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mioption_runtime.futu.policy import TradePolicy  # noqa: E402
from mioption_runtime.seller.follow import follow_once, stop_path  # noqa: E402
from mioption_runtime.seller.scan import DEFAULT_WATCHLIST  # noqa: E402
from mioption_runtime.seller.store import SellerStore, default_root  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(
        description=(
            "Follow adopted local cards. Research-only dry-run; --submit is rejected. "
            "Touch STOP in the seller data dir to halt. No osmtrade API."
        )
    )
    p.add_argument("--submit", action="store_true", help="Rejected: research-only workflow")
    p.add_argument(
        "--legs",
        choices=["none", "sequential"],
        default="none",
        help="Legacy flag; sequential submission is rejected",
    )
    p.add_argument("--whitelist", default=",".join(DEFAULT_WATCHLIST))
    args = p.parse_args()
    store = SellerStore(default_root())
    policy = TradePolicy()
    names = [x.strip() for x in args.whitelist.split(",") if x.strip()]
    with store.transaction():
        payload = follow_once(
            store,
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
