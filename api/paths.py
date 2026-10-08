"""仓库产物定位：runs/ chains/ reports/ seller store。只读。"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = REPO_ROOT / "runs"
CHAINS_DIR = REPO_ROOT / "chains"
REPORTS_DIR = REPO_ROOT / "reports"
SELLER_DIR = REPO_ROOT / "runtime" / "data" / "live" / "seller"
STRATEGIES_DIR = REPO_ROOT / "knowledge" / "wiki" / "strategies"
CONFIG_PATH = REPO_ROOT / "signal_chain" / "config.yaml"
VOL_BASIS_DIR = REPO_ROOT / "runtime" / "data" / "live" / "vol_basis"

_RUN_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.json$")


def run_dates() -> list[str]:
    out = []
    for path in RUNS_DIR.glob("*.json"):
        m = _RUN_RE.match(path.name)
        if m:
            out.append(m.group(1))
    return sorted(out)


def latest_run_date() -> str | None:
    dates = run_dates()
    return dates[-1] if dates else None


def load_run(day: str) -> dict:
    return json.loads((RUNS_DIR / f"{day}.json").read_text(encoding="utf-8"))


def load_coverage(day: str) -> dict:
    path = RUNS_DIR / f"{day}.coverage.json"
    if not path.is_file():
        return {"date": day, "tickers": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def load_chain(day: str, ticker: str) -> dict | None:
    path = CHAINS_DIR / day / f"{ticker}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_report(day: str, ticker: str) -> str | None:
    path = REPORTS_DIR / day / f"{ticker}.md"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def chain_dates() -> list[str]:
    if not CHAINS_DIR.is_dir():
        return []
    return sorted(p.name for p in CHAINS_DIR.iterdir() if p.is_dir())


def latest_chain_date() -> str | None:
    dates = chain_dates()
    return dates[-1] if dates else None


def as_date(day: str) -> date:
    return date.fromisoformat(day)


def load_vol_basis(ticker: str) -> dict | None:
    path = VOL_BASIS_DIR / f"{ticker}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
