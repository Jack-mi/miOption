"""落盘：signals/ chains/ reports/ runs/ 台账。全部由 orchestrator 写，LLM 不写文件。"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .config import CHAINS_DIR, REPORTS_DIR, RUNS_DIR, SIGNALS_DIR, ensure_dirs


def _dump(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    return obj


def append_signal(day: date, ticker: str, record: BaseModel) -> Path:
    ensure_dirs()
    path = SIGNALS_DIR / day.isoformat() / f"{ticker}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(_dump(record), ensure_ascii=False) + "\n")
    return path


def write_chain(day: date, ticker: str, chain: BaseModel) -> Path:
    ensure_dirs()
    path = CHAINS_DIR / day.isoformat() / f"{ticker}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_dump(chain), ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def write_report(day: date, ticker: str, markdown: str) -> Path:
    ensure_dirs()
    path = REPORTS_DIR / day.isoformat() / f"{ticker}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path


def write_coverage(
    day: date, ticker: str, snapshot: BaseModel,
    sources: list | None = None, runs_dir: Path | None = None,
) -> Path:
    """runs/{date}.coverage.json — 同一运行日的字段覆盖，不含价格。"""
    from .options.underlying_fetch import coverage_entry

    root = runs_dir or RUNS_DIR
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{day.isoformat()}.coverage.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"date": day.isoformat(), "tickers": {}}
    data["tickers"][ticker] = coverage_entry(snapshot, sources)  # type: ignore[arg-type]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


class RunLedger:
    """runs/{date}.json - 每标的的引擎状态、thread id、降级标记、耗时。"""

    def __init__(self, day: date):
        ensure_dirs()
        self.path = RUNS_DIR / f"{day.isoformat()}.json"
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data: dict[str, Any] = {"date": day.isoformat(), "tickers": {}}

    def record(self, ticker: str, entry: dict[str, Any]) -> None:
        entry = dict(entry)
        entry["updated_at"] = datetime.now(timezone.utc).isoformat()
        stored = self.data["tickers"].setdefault(ticker, {})
        if entry.get("error") is None and "error" in entry:
            stored.pop("error", None)      # None 语义 = 清除陈旧错误
            entry.pop("error")
        stored.update(entry)
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8"
        )
