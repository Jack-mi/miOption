#!/usr/bin/env python3
"""Pull live Futu equity snapshot + N-day option chain + option params. No orders."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mioption_runtime.futu.quote import pull_underlying_pack  # noqa: E402
from mioption_runtime.futu.quote_store import QuoteStore  # noqa: E402
from mioption_runtime.seller.scan import resolve_symbol  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Pull live underlying + option pack from OpenD.")
    p.add_argument("underlying", nargs="?", default="US.BIDU")
    p.add_argument("--days", type=int, default=60)
    p.add_argument(
        "--out",
        default="",
        help="JSON path (default runtime/data/quotes/<code>.json). Debug dump only.",
    )
    p.add_argument("--no-json", action="store_true", help="Skip writing the debug JSON dump.")
    args = p.parse_args()
    os.environ["MIOPTION_FUTU_MOCK"] = "0"
    underlying = resolve_symbol(args.underlying) or args.underlying
    pack = pull_underlying_pack(underlying, days=args.days)
    store = QuoteStore()
    pull_id = store.replace_current(pack)
    out: Path | None = None
    if not args.no_json:
        out = Path(args.out) if args.out else store.path.parent / "quotes" / f"{underlying}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    eq = pack["equity"]
    chain = pack["chain"]
    cov = pack["coverage"]
    print(
        json.dumps(
            {
                "ok": pack["ok"],
                "sqlite": str(store.path),
                "pull_id": pull_id,
                "out": str(out) if out else None,
                "underlying": pack["underlying"],
                "days": pack["days"],
                "windows": pack["windows"],
                "equity_last": eq.get("last_price"),
                "equity_name": eq.get("name"),
                "equity_fields": len(eq),
                "chain_count": chain["count"],
                "expiries": chain["expiries"],
                "calls": chain["call_count"],
                "puts": chain["put_count"],
                "option_snapshots": cov["option_snapshots"],
                "with_quote": cov["with_quote"],
                "with_greeks": cov["with_greeks"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
