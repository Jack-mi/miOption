"""每日刷新共享宏观层：FRED -> Supabase。"""

from __future__ import annotations

import argparse

from .keys import load_keys
from .macro import refresh_macro


def main() -> None:
    parser = argparse.ArgumentParser(description="把 FRED 最新宏观观测写入 Supabase 共享层")
    parser.parse_args()
    keys = load_keys()
    points, rows = refresh_macro(
        keys.get("FRED_API_KEY"),
        keys.get("SUPABASE_SERVICE_ROLE_KEY"),
    )
    for row in rows:
        print(f"{row.id} {row.field} {row.state} {row.note}")
    if not points or any(row.state != "used" for row in rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
