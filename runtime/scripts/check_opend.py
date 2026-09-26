#!/usr/bin/env python3
"""Phase A: diagnose OpenD + futu-api from the runtime package."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mioption_runtime.futu.opend import probe_permissions  # noqa: E402


def main() -> int:
    report = probe_permissions()
    print(json.dumps(report, indent=2, default=str))
    if report.get("tcp_open") and report.get("futu_importable") and report.get("quote_ctx_ok"):
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
