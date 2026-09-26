"""Option chain / snapshot backends (live Futu or in-process mock)."""

from __future__ import annotations

import math
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Protocol

CHAIN_WINDOW_DAYS = 30
SNAPSHOT_CHUNK = 400


def jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, bool)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return jsonable(item())
        except Exception:
            pass
    text = str(value)
    if text in ("nan", "NaN", "NaT", "None", "<NA>", "N/A"):
        return None
    return text


def chain_date_windows(days: int, today: date | None = None) -> list[tuple[str, str]]:
    """Inclusive expiry windows, each at most 30 calendar days (Futu limit).

    `days=60` covers today through today+60 (a 60-day horizon), split into
    Futu-legal spans. Listed expiries inside that horizon are the chain;
    later months are peeked separately so the board can say why it stops.
    """
    if days < 1:
        raise ValueError("days must be >= 1")
    today = today or date.today()
    last = today + timedelta(days=days)
    out: list[tuple[str, str]] = []
    start = today
    while start <= last:
        end = min(start + timedelta(days=CHAIN_WINDOW_DAYS - 1), last)
        out.append((start.isoformat(), end.isoformat()))
        start = end + timedelta(days=1)
    return out


def peek_windows_after(window_end: str, *, spans: int = 2) -> list[tuple[str, str]]:
    """Next Futu-legal spans after the requested horizon, to detect later listings."""
    start = date.fromisoformat(window_end[:10]) + timedelta(days=1)
    out: list[tuple[str, str]] = []
    for _ in range(max(1, spans)):
        end = start + timedelta(days=CHAIN_WINDOW_DAYS - 1)
        out.append((start.isoformat(), end.isoformat()))
        start = end + timedelta(days=1)
    return out


def _frame_records(data: Any) -> list[dict[str, Any]]:
    if data is None or getattr(data, "empty", False):
        return []
    rows: list[dict[str, Any]] = []
    for _, row in data.iterrows():
        rows.append({str(k): jsonable(v) for k, v in row.items()})
    return rows


@dataclass
class OptionContract:
    code: str
    underlying: str
    strike: float
    expiry: str
    option_type: str  # CALL | PUT
    bid: float
    ask: float
    last: float
    delta: float | None = None

    def mid(self) -> float:
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2.0
        return self.last

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class QuoteBackend(Protocol):
    def snapshot(self, code: str) -> dict[str, Any]: ...

    def option_chain(
        self,
        underlying: str,
        *,
        expiry: str | None = None,
    ) -> list[OptionContract]: ...


class MockQuoteBackend:
    """Deterministic chain for dry-run / tests without OpenD."""

    def snapshot(self, code: str) -> dict[str, Any]:
        for contract in self.option_chain(code.split("_")[0] if "_" in code else code):
            if contract.code == code:
                return {
                    "code": code,
                    "last_price": contract.last,
                    "bid": contract.bid,
                    "ask": contract.ask,
                    "bid_price": contract.bid,
                    "ask_price": contract.ask,
                    "option_delta": contract.delta,
                    "source": "mock",
                }
        return {
            "code": code,
            "last_price": 100.0,
            "bid": 99.95,
            "ask": 100.05,
            "bid_price": 99.95,
            "ask_price": 100.05,
            "source": "mock",
        }

    def snapshots(self, codes: list[str]) -> dict[str, dict[str, Any]]:
        return {code: self.snapshot(code) for code in codes}

    def option_chain(
        self,
        underlying: str,
        *,
        expiry: str | None = None,
    ) -> list[OptionContract]:
        exp = expiry or (date.today() + timedelta(days=14)).isoformat()
        # Widths of $5 around a 100 spot so bull-put 95/90 and bear-call 105/110 scan.
        strikes = [90.0, 95.0, 100.0, 105.0, 110.0]
        put_delta = {90.0: -0.12, 95.0: -0.22, 100.0: -0.50, 105.0: -0.70, 110.0: -0.85}
        call_delta = {90.0: 0.85, 95.0: 0.70, 100.0: 0.50, 105.0: 0.22, 110.0: 0.12}
        out: list[OptionContract] = []
        for k in strikes:
            for opt in ("CALL", "PUT"):
                otm = (100.0 - k) if opt == "PUT" else (k - 100.0)
                if otm < 0:
                    mid = abs(otm) + (1.4 if opt == "CALL" else 0.9)
                elif opt == "PUT":
                    mid = max(0.25, 1.90 - otm * 0.20)
                else:
                    mid = max(0.30, 1.55 - otm * 0.18)
                out.append(
                    OptionContract(
                        code=f"{underlying}_{exp}_{opt[0]}{k:g}",
                        underlying=underlying,
                        strike=k,
                        expiry=exp,
                        option_type=opt,
                        bid=round(mid - 0.05, 2),
                        ask=round(mid + 0.05, 2),
                        last=round(mid, 2),
                        delta=(call_delta if opt == "CALL" else put_delta)[k],
                    )
                )
        return out


class FutuQuoteBackend:
    def __init__(self, host: str = "127.0.0.1", port: int = 11111):
        self.host = host
        self.port = port

    def _context(self):
        from futu import OpenQuoteContext
        from .opend import tcp_reachable

        if not tcp_reachable(self.host, self.port):
            raise RuntimeError(f"OpenD not reachable at {self.host}:{self.port}; start and login OpenD")
        return OpenQuoteContext(host=self.host, port=self.port)

    def snapshot(self, code: str) -> dict[str, Any]:
        from futu import OpenQuoteContext, RET_OK

        ctx = self._context()
        try:
            ret, data = ctx.get_market_snapshot([code])
            if ret != RET_OK:
                raise RuntimeError(f"snapshot failed: {data}")
            row = data.iloc[0].to_dict()
            row["source"] = "futu"
            return row
        finally:
            ctx.close()

    def snapshots(self, codes: list[str]) -> dict[str, dict[str, Any]]:
        from futu import OpenQuoteContext

        ctx = self._context()
        try:
            return _snapshots_with_ctx(ctx, codes)
        finally:
            ctx.close()

    def option_chain(
        self,
        underlying: str,
        *,
        expiry: str | None = None,
        days: int | None = None,
    ) -> list[OptionContract]:
        from futu import OpenQuoteContext

        ctx = self._context()
        try:
            rows = _chain_rows_with_ctx(ctx, underlying, days=days)
            contracts: list[OptionContract] = []
            for row in rows:
                exp = str(row.get("strike_time") or row.get("expiry_date") or "")
                if expiry and expiry not in exp:
                    continue
                opt_s = "PUT" if "PUT" in str(row.get("option_type") or "").upper() else "CALL"
                contracts.append(
                    OptionContract(
                        code=str(row.get("code")),
                        underlying=underlying,
                        strike=float(row.get("strike_price") or 0),
                        expiry=exp,
                        option_type=opt_s,
                        bid=float(row.get("bid_price") or 0),
                        ask=float(row.get("ask_price") or 0),
                        last=float(row.get("last_price") or 0),
                        delta=None,
                    )
                )
            return contracts
        finally:
            ctx.close()


def get_quote_backend(
    *,
    prefer_mock: bool | None = None,
    host: str = "127.0.0.1",
    port: int = 11111,
) -> QuoteBackend:
    if prefer_mock is None:
        prefer_mock = os.environ.get("MIOPTION_FUTU_MOCK", "1") == "1"
    if prefer_mock:
        return MockQuoteBackend()
    return FutuQuoteBackend(host=host, port=port)


def mock_underlying_pack(underlying: str, *, days: int = 60) -> dict[str, Any]:
    backend = MockQuoteBackend()
    windows = chain_date_windows(days)
    contracts = [contract for contract in backend.option_chain(underlying) if contract.expiry <= windows[-1][1]]
    return {
        "ok": True,
        "underlying": underlying,
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "source": "mock",
        "days": days,
        "windows": [{"start": start, "end": end} for start, end in windows],
        "equity": backend.snapshot(underlying),
        "options": [
            {**contract.as_dict(), "strike_time": contract.expiry, "option_strike_price": contract.strike}
            for contract in contracts
        ],
        "coverage": {"chain_contracts": len(contracts), "with_quote": len(contracts), "with_greeks": len(contracts)},
    }


def _snapshots_with_ctx(ctx: Any, codes: list[str]) -> dict[str, dict[str, Any]]:
    from futu import RET_OK

    out: dict[str, dict[str, Any]] = {}
    unique = [code for code in dict.fromkeys(codes) if code]
    for i in range(0, len(unique), SNAPSHOT_CHUNK):
        chunk = unique[i : i + SNAPSHOT_CHUNK]
        ret, data = ctx.get_market_snapshot(chunk)
        if ret != RET_OK:
            raise RuntimeError(f"snapshot failed: {data}")
        for rec in _frame_records(data):
            rec["source"] = "futu"
            code = str(rec.get("code") or "")
            if code:
                out[code] = rec
    return out


def _chain_rows_with_ctx(
    ctx: Any,
    underlying: str,
    *,
    days: int | None = None,
) -> list[dict[str, Any]]:
    from futu import RET_OK

    windows = chain_date_windows(days) if days else [None]
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for window in windows:
        if window is None:
            ret, data = ctx.get_option_chain(underlying)
        else:
            start, end = window
            ret, data = ctx.get_option_chain(underlying, start=start, end=end)
        if ret != RET_OK:
            raise RuntimeError(f"option_chain failed: {data}")
        for rec in _frame_records(data):
            code = str(rec.get("code") or "")
            if not code or code in seen:
                continue
            seen.add(code)
            rows.append(rec)
    return rows


def _expiries_in_span(ctx: Any, underlying: str, start: str, end: str) -> list[str]:
    from futu import RET_OK

    ret, data = ctx.get_option_chain(underlying, start=start, end=end)
    if ret != RET_OK:
        return []
    return sorted(
        {str(rec.get("strike_time") or "")[:10] for rec in _frame_records(data) if rec.get("strike_time")}
    )


def _peek_beyond_expiries(ctx: Any, underlying: str, window_end: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for start, end in peek_windows_after(window_end):
        for expiry in _expiries_in_span(ctx, underlying, start, end):
            if expiry not in seen:
                seen.add(expiry)
                found.append(expiry)
        if found:
            break
    return found


def pull_underlying_pack(
    underlying: str,
    *,
    days: int = 60,
    host: str = "127.0.0.1",
    port: int = 11111,
) -> dict[str, Any]:
    """Live OpenD pull: full equity snapshot + N-day chain + option snapshots/greeks."""
    from futu import OpenQuoteContext, RET_OK

    from .opend import connect

    status = connect(host, port, probe_trade=False)
    if not (status.tcp_open and status.futu_importable and status.quote_ctx_ok):
        raise RuntimeError(status.message or "OpenD unavailable")

    windows = chain_date_windows(days)
    ctx = OpenQuoteContext(host=host, port=port)
    beyond: list[str] = []
    try:
        ret, eq = ctx.get_market_snapshot([underlying])
        if ret != RET_OK:
            raise RuntimeError(f"equity snapshot failed: {eq}")
        equity_rows = _frame_records(eq)
        if not equity_rows:
            raise RuntimeError(f"no equity snapshot for {underlying}")
        equity = equity_rows[0]
        equity["source"] = "futu"
        chain_rows = _chain_rows_with_ctx(ctx, underlying, days=days)
        option_snaps = _snapshots_with_ctx(ctx, [str(r["code"]) for r in chain_rows])
        try:
            beyond = _peek_beyond_expiries(ctx, underlying, windows[-1][1]) if windows else []
        except Exception:
            beyond = []
    finally:
        ctx.close()

    options: list[dict[str, Any]] = []
    greeks = 0
    quoted = 0
    for row in chain_rows:
        code = str(row["code"])
        snap = option_snaps.get(code) or {}
        merged = {**row, **snap}
        merged["code"] = code
        merged["source"] = "futu"
        options.append(merged)
        if snap.get("option_delta") is not None or snap.get("option_implied_volatility") is not None:
            greeks += 1
        if (snap.get("bid_price") or 0) or (snap.get("ask_price") or 0) or (snap.get("last_price") or 0):
            quoted += 1

    expiries = sorted({str(r.get("strike_time") or "")[:10] for r in chain_rows if r.get("strike_time")})
    return {
        "ok": True,
        "underlying": underlying,
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "source": "futu",
        "days": days,
        "windows": [{"start": a, "end": b} for a, b in windows],
        "equity": equity,
        "chain": {
            "count": len(chain_rows),
            "expiries": expiries,
            "call_count": sum(1 for r in chain_rows if "CALL" in str(r.get("option_type") or "").upper()),
            "put_count": sum(1 for r in chain_rows if "PUT" in str(r.get("option_type") or "").upper()),
            "contracts": chain_rows,
        },
        "options": options,
        "coverage": {
            "chain_contracts": len(chain_rows),
            "option_snapshots": len(option_snaps),
            "with_quote": quoted,
            "with_greeks": greeks,
            "window_start": windows[0][0] if windows else "",
            "window_end": windows[-1][1] if windows else "",
            "listed_last": expiries[-1] if expiries else "",
            "next_beyond": beyond,
        },
    }
