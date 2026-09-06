"""Option chain / snapshot backends (live Futu or in-process mock)."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any, Protocol


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
        exp = expiry or (date.today() + timedelta(days=30)).isoformat()
        strikes = [95.0, 100.0, 105.0]
        out: list[OptionContract] = []
        for k in strikes:
            for opt, delta in (
                ("CALL", 0.5 if k == 100 else (0.7 if k < 100 else 0.3)),
                ("PUT", -0.5 if k == 100 else (-0.3 if k < 100 else -0.7)),
            ):
                if opt == "CALL":
                    intrinsic = max(0.0, 100.0 - k)
                else:
                    intrinsic = max(0.0, k - 100.0)
                mid = max(0.5, intrinsic + 1.5)
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
                        delta=delta,
                    )
                )
        return out


class FutuQuoteBackend:
    def __init__(self, host: str = "127.0.0.1", port: int = 11111):
        self.host = host
        self.port = port

    def snapshot(self, code: str) -> dict[str, Any]:
        from futu import OpenQuoteContext, RET_OK

        ctx = OpenQuoteContext(host=self.host, port=self.port)
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
        from futu import OpenQuoteContext, RET_OK

        out: dict[str, dict[str, Any]] = {}
        ctx = OpenQuoteContext(host=self.host, port=self.port)
        try:
            for i in range(0, len(codes), 200):
                chunk = codes[i : i + 200]
                ret, data = ctx.get_market_snapshot(chunk)
                if ret != RET_OK:
                    raise RuntimeError(f"snapshot failed: {data}")
                for _, row in data.iterrows():
                    rec = row.to_dict()
                    rec["source"] = "futu"
                    out[str(rec.get("code"))] = rec
            return out
        finally:
            ctx.close()

    def option_chain(
        self,
        underlying: str,
        *,
        expiry: str | None = None,
    ) -> list[OptionContract]:
        from futu import OpenQuoteContext, RET_OK, OptionType

        ctx = OpenQuoteContext(host=self.host, port=self.port)
        try:
            ret, data = ctx.get_option_chain(underlying)
            if ret != RET_OK:
                raise RuntimeError(f"option_chain failed: {data}")
            contracts: list[OptionContract] = []
            for _, row in data.iterrows():
                exp = str(row.get("strike_time") or row.get("expiry_date") or "")
                if expiry and expiry not in exp:
                    continue
                opt = row.get("option_type")
                opt_s = "CALL" if opt in (OptionType.CALL, "CALL", "Call") else "PUT"
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
    from .opend import connect

    status = connect(host, port, probe_trade=False)
    if not (status.tcp_open and status.futu_importable and status.quote_ctx_ok):
        raise RuntimeError(status.message or "OpenD unavailable; set MIOPTION_FUTU_MOCK=1")
    return FutuQuoteBackend(host=host, port=port)
