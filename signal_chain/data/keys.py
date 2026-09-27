"""免费 key 从环境变量、仓库根 .env 或 signal_chain/.env.data 读。文件不入库。"""

from __future__ import annotations

import os
from pathlib import Path

from ..config import REPO_ROOT

KEY_FILE = REPO_ROOT / "signal_chain" / ".env.data"
ROOT_ENV = REPO_ROOT / ".env"
_NAMES = (
    "FMP_API_KEY",
    "FINNHUB_API_KEY",
    "FRED_API_KEY",
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "REDDIT_USERNAME",
    "EDGAR_CONTACT",
)


def _parse(path: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    if not path.exists():
        return found
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        name, value = text.split("=", 1)
        found[name.strip()] = value.strip().strip('"').strip("'")
    return found


def load_keys(path: Path | None = None) -> dict[str, str]:
    if path is not None:
        file_vals = _parse(path)
    else:
        file_vals = _parse(KEY_FILE)
        for name, value in _parse(ROOT_ENV).items():
            file_vals.setdefault(name, value)
    found = {name: os.environ.get(name) or file_vals.get(name, "") for name in _NAMES}
    if not found["FMP_API_KEY"]:
        found["FMP_API_KEY"] = os.environ.get("FMP_KEY") or file_vals.get("FMP_KEY", "")
    return found
