"""Local revision-preserving daily bars; vendor prices never leave this machine."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from ..config import REPO_ROOT

DB_PATH = REPO_ROOT / "runtime/data/live/daily_bars.sqlite"


class DailyStore:
    def __init__(self, path: Path = DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("""create table if not exists bars (
                ticker text not null, day text not null, source text not null,
                adjusted integer not null, digest text not null, fetched_at text not null,
                payload text not null, primary key(ticker, day, source, adjusted, digest)
            )""")
        self.path.chmod(0o600)

    def read(self, ticker: str, source: str, adjusted: bool, until: date) -> list[dict]:
        with sqlite3.connect(self.path) as db:
            rows = db.execute("""select day, payload from bars where ticker = ? and source = ?
                and adjusted = ? and day <= ? order by day, fetched_at, rowid""",
                (ticker, source, int(adjusted), until.isoformat())).fetchall()
        return list({day: json.loads(payload) for day, payload in rows}.values())

    def save(self, ticker: str, source: str, adjusted: bool, bars: list[dict],
             completed: date, fetched_at: datetime | None = None) -> int:
        timestamp = (fetched_at or datetime.now(timezone.utc)).isoformat()
        records = []
        for bar in bars:
            day = str(bar.get("trade_date") or "")[:10]
            if not day or day > completed.isoformat() or bar.get("close") is None:
                continue
            payload = json.dumps(bar, sort_keys=True, separators=(",", ":"), default=str)
            digest = hashlib.sha256(payload.encode()).hexdigest()
            records.append((ticker, day, source, int(adjusted), digest, timestamp, payload))
        with sqlite3.connect(self.path) as db:
            db.executemany("insert or ignore into bars values (?, ?, ?, ?, ?, ?, ?)", records)
        return len(records)
