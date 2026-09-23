"""SQLite archive of live equity + option packs. Not the seller-card store."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KEEP_PULLS = 3
MAX_QUOTE_AGE_SECONDS = 3 * 24 * 60 * 60


def freshness(pulled_at: str) -> dict[str, Any]:
    try:
        timestamp = datetime.fromisoformat(pulled_at.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        age = max(0, (datetime.now(timezone.utc) - timestamp).total_seconds())
    except (ValueError, TypeError):
        return {"stale": True, "age_seconds": None}
    return {"stale": age > MAX_QUOTE_AGE_SECONDS, "age_seconds": round(age)}

CONTRACT_COLS = (
    "bid",
    "ask",
    "last",
    "delta",
    "gamma",
    "vega",
    "theta",
    "rho",
    "iv",
    "oi",
    "premium",
    "dte",
    "bid_vol",
    "ask_vol",
)

_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "bid": ("bid_price", "bid"),
    "ask": ("ask_price", "ask"),
    "last": ("last_price", "last"),
    "delta": ("option_delta", "delta"),
    "gamma": ("option_gamma", "gamma"),
    "vega": ("option_vega", "vega"),
    "theta": ("option_theta", "theta"),
    "rho": ("option_rho", "rho"),
    "iv": ("option_implied_volatility", "iv"),
    "oi": ("option_open_interest", "oi"),
    "premium": ("option_premium", "premium"),
    "dte": ("option_expiry_date_distance", "dte"),
    "bid_vol": ("bid_vol",),
    "ask_vol": ("ask_vol",),
}

_EXTRACTED = {"code", "expiry", "option_type", "strike", *CONTRACT_COLS}
for aliases in _FIELD_ALIASES.values():
    _EXTRACTED.update(aliases)
_EXTRACTED.update({"strike_time", "option_type", "strike_price", "option_strike_price", "source"})


def default_db_path() -> Path:
    env = os.environ.get("MIOPTION_QUOTES_DB")
    if env:
        return Path(env)
    mode = "mock" if os.environ.get("MIOPTION_FUTU_MOCK", "1") == "1" else "live"
    return Path(__file__).resolve().parents[2] / "data" / mode / "quotes.sqlite"


def _json_dump(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _num(raw: Any) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value != value:  # NaN
        return None
    return value


def _option_type(raw: Any) -> str:
    return "PUT" if "PUT" in str(raw or "").upper() else "CALL"


def _strike(row: dict[str, Any]) -> float:
    return float(_num(row.get("option_strike_price")) or _num(row.get("strike_price")) or 0)


def _expiry(row: dict[str, Any]) -> str:
    return str(row.get("strike_time") or row.get("expiry") or "")[:10]


def group_by_expiry(contracts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[float, dict[str, Any]]] = {}
    for contract in contracts:
        expiry = str(contract.get("expiry") or "")
        strike = float(contract.get("strike") or 0)
        by_strike = buckets.setdefault(expiry, {})
        if strike not in by_strike:
            by_strike[strike] = {"strike": strike, "call": None, "put": None}
        side = "put" if str(contract.get("option_type") or "").upper() == "PUT" else "call"
        by_strike[strike][side] = contract
    return [
        {"expiry": expiry, "strikes": [by_strike[s] for s in sorted(by_strike)]}
        for expiry, by_strike in sorted(buckets.items())
    ]


def contract_row(option: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "code": str(option.get("code") or ""),
        "expiry": _expiry(option),
        "option_type": _option_type(option.get("option_type")),
        "strike": _strike(option),
    }
    for col in CONTRACT_COLS:
        for key in _FIELD_ALIASES[col]:
            n = _num(option.get(key))
            if n is not None:
                out[col] = n
                break
        else:
            out[col] = None
    extra = {k: v for k, v in option.items() if k not in _EXTRACTED}
    out["extra"] = extra
    return out


class QuoteStore:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS pulls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    underlying TEXT NOT NULL,
                    pulled_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    days INTEGER NOT NULL,
                    windows_json TEXT NOT NULL,
                    coverage_json TEXT NOT NULL,
                    is_current INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS equity (
                    pull_id INTEGER PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY (pull_id) REFERENCES pulls(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS contracts (
                    pull_id INTEGER NOT NULL,
                    code TEXT NOT NULL,
                    expiry TEXT NOT NULL,
                    option_type TEXT NOT NULL,
                    strike REAL NOT NULL,
                    bid REAL,
                    ask REAL,
                    last REAL,
                    delta REAL,
                    gamma REAL,
                    vega REAL,
                    theta REAL,
                    rho REAL,
                    iv REAL,
                    oi REAL,
                    premium REAL,
                    dte REAL,
                    bid_vol REAL,
                    ask_vol REAL,
                    extra_json TEXT NOT NULL,
                    PRIMARY KEY (pull_id, code),
                    FOREIGN KEY (pull_id) REFERENCES pulls(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_pulls_underlying_current
                    ON pulls (underlying, is_current);
                CREATE INDEX IF NOT EXISTS idx_contracts_expiry
                    ON contracts (pull_id, expiry, strike);
                """
            )

    def replace_current(self, pack: dict[str, Any], *, keep: int = KEEP_PULLS) -> int:
        underlying = str(pack["underlying"])
        options = list(pack.get("options") or [])
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO pulls (
                    underlying, pulled_at, source, days, windows_json, coverage_json, is_current
                ) VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    underlying,
                    str(pack.get("pulled_at") or ""),
                    str(pack.get("source") or "futu"),
                    int(pack.get("days") or 60),
                    _json_dump(pack.get("windows") or []),
                    _json_dump(pack.get("coverage") or {}),
                ),
            )
            pull_id = int(cur.lastrowid)
            conn.execute(
                "INSERT INTO equity (pull_id, payload_json) VALUES (?, ?)",
                (pull_id, _json_dump(pack.get("equity") or {})),
            )
            for option in options:
                row = contract_row(option)
                if not row["code"]:
                    continue
                conn.execute(
                    """
                    INSERT INTO contracts (
                        pull_id, code, expiry, option_type, strike,
                        bid, ask, last, delta, gamma, vega, theta, rho,
                        iv, oi, premium, dte, bid_vol, ask_vol, extra_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pull_id,
                        row["code"],
                        row["expiry"],
                        row["option_type"],
                        row["strike"],
                        row["bid"],
                        row["ask"],
                        row["last"],
                        row["delta"],
                        row["gamma"],
                        row["vega"],
                        row["theta"],
                        row["rho"],
                        row["iv"],
                        row["oi"],
                        row["premium"],
                        row["dte"],
                        row["bid_vol"],
                        row["ask_vol"],
                        _json_dump(row["extra"]),
                    ),
                )
            conn.execute(
                "UPDATE pulls SET is_current = 0 WHERE underlying = ?",
                (underlying,),
            )
            conn.execute("UPDATE pulls SET is_current = 1 WHERE id = ?", (pull_id,))
            ids = conn.execute(
                "SELECT id FROM pulls WHERE underlying = ? ORDER BY id DESC",
                (underlying,),
            ).fetchall()
            for item in ids[keep:]:
                conn.execute("DELETE FROM pulls WHERE id = ?", (int(item["id"]),))
            return pull_id

    def current(self, underlying: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            pull = conn.execute(
                "SELECT * FROM pulls WHERE underlying = ? AND is_current = 1",
                (underlying,),
            ).fetchone()
            if pull is None:
                return None
            equity_row = conn.execute(
                "SELECT payload_json FROM equity WHERE pull_id = ?",
                (pull["id"],),
            ).fetchone()
            contracts = conn.execute(
                """
                SELECT code, expiry, option_type, strike,
                       bid, ask, last, delta, gamma, vega, theta, rho,
                       iv, oi, premium, dte, bid_vol, ask_vol
                FROM contracts
                WHERE pull_id = ?
                ORDER BY expiry, strike, option_type
                """,
                (pull["id"],),
            ).fetchall()
            equity = json.loads(equity_row["payload_json"]) if equity_row else {}
            rows = [dict(c) for c in contracts]
            expiries = sorted({str(c["expiry"]) for c in rows if c["expiry"]})
            coverage = json.loads(pull["coverage_json"] or "{}")
            return {
                "ok": True,
                "place_order": False,
                "underlying": pull["underlying"],
                "pulled_at": pull["pulled_at"],
                "source": pull["source"],
                "days": pull["days"],
                "windows": json.loads(pull["windows_json"] or "[]"),
                "coverage": coverage,
                "equity": equity,
                "expiries": expiries,
                "contracts": rows,
                "chain": group_by_expiry(rows),
                "count": len(rows),
                **freshness(pull["pulled_at"]),
            }

    def get_contract(self, underlying: str, code: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT c.*, p.underlying, p.pulled_at
                FROM contracts c
                JOIN pulls p ON p.id = c.pull_id
                WHERE p.underlying = ? AND p.is_current = 1 AND c.code = ?
                """,
                (underlying, code),
            ).fetchone()
            if row is None:
                return None
            payload = dict(row)
            extra = json.loads(payload.pop("extra_json") or "{}")
            payload["extra"] = extra
            payload["place_order"] = False
            payload["ok"] = True
            return payload

    def pull_count(self, underlying: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM pulls WHERE underlying = ?",
                (underlying,),
            ).fetchone()
            return int(row["n"]) if row else 0


class StoredQuoteBackend:
    def __init__(self, pack: dict[str, Any]):
        if pack.get("stale", True):
            raise ValueError("quote_snapshot_stale: refresh the option chain before monitoring")
        self.pack = pack

    def snapshot(self, code: str) -> dict[str, Any]:
        if code == self.pack["underlying"]:
            return dict(self.pack["equity"])
        for contract in self.pack["contracts"]:
            if contract["code"] == code:
                return {**contract, "source": self.pack["source"], "pulled_at": self.pack["pulled_at"]}
        raise ValueError(f"contract_not_in_snapshot: {code}; refresh the option chain")

    def option_chain(self, underlying: str, *, expiry: str | None = None) -> list:
        from .quote import OptionContract

        return [
            OptionContract(
                code=row["code"], underlying=underlying, strike=row["strike"], expiry=row["expiry"],
                option_type=row["option_type"], bid=row["bid"] or 0, ask=row["ask"] or 0,
                last=row["last"] or 0, delta=row["delta"],
            )
            for row in self.pack["contracts"]
            if underlying == self.pack["underlying"] and (not expiry or row["expiry"] == expiry)
        ]
