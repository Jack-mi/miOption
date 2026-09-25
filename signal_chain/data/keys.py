"""免费 key 只从环境变量或 signal_chain/.env.data 读。文件不入库。"""

from __future__ import annotations

import os
from pathlib import Path

from ..config import REPO_ROOT

KEY_FILE = REPO_ROOT / "signal_chain" / ".env.data"
_NAMES = (
    "ALPHAVANTAGE_API_KEY",
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "EDGAR_CONTACT",
)


def load_keys(path: Path | None = None) -> dict[str, str]:
    file_vals: dict[str, str] = {}
    src = path if path is not None else KEY_FILE
    if src.exists():
        for line in src.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if not text or text.startswith("#") or "=" not in text:
                continue
            name, value = text.split("=", 1)
            file_vals[name.strip()] = value.strip()
    return {name: os.environ.get(name) or file_vals.get(name, "") for name in _NAMES}
