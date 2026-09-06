"""Order placement backends (SIMULATE default; mock for dry-run)."""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from .policy import PolicyError, TradeEnv, TradePolicy


@dataclass
class Leg:
    code: str
    side: str  # BUY | SELL
    qty: float
    price: float | None = None
    option_type: str | None = None
    strike: float | None = None
    expiry: str | None = None


@dataclass
class OrderRequest:
    underlying: str
    legs: list[Leg]
    structure_id: str | None = None
    env: TradeEnv = TradeEnv.SIMULATE
    notional: float = 0.0
    naked_short: bool = False
    client_order_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])

    def as_dict(self) -> dict[str, Any]:
        return {
            "underlying": self.underlying,
            "structure_id": self.structure_id,
            "env": self.env.value,
            "notional": self.notional,
            "naked_short": self.naked_short,
            "client_order_id": self.client_order_id,
            "legs": [asdict(leg) for leg in self.legs],
        }


@dataclass
class OrderResult:
    ok: bool
    order_id: str
    env: str
    message: str
    request: dict[str, Any]
    fills: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class TradeBackend(Protocol):
    policy: TradePolicy

    def place(self, request: OrderRequest) -> OrderResult: ...

    def cancel(self, order_id: str) -> dict[str, Any]: ...

    def positions(self) -> list[dict[str, Any]]: ...

    def funds(self) -> dict[str, Any]: ...


class MockTradeBackend:
    def __init__(self, policy: TradePolicy | None = None):
        self.policy = policy or TradePolicy()
        self._orders: dict[str, OrderResult] = {}
        self._positions: list[dict[str, Any]] = []

    def place(self, request: OrderRequest) -> OrderResult:
        if request.env != self.policy.env and request.env == TradeEnv.REAL:
            self.policy.env = request.env
        try:
            self.policy.authorize_open(
                notional=request.notional,
                naked_short=request.naked_short,
            )
        except PolicyError as exc:
            return OrderResult(
                ok=False,
                order_id="",
                env=request.env.value,
                message=exc.message,
                request=request.as_dict(),
            )
        self.policy.note_order(time.time())
        order_id = f"mock-{request.client_order_id}"
        fills = [
            {
                "code": leg.code,
                "side": leg.side,
                "qty": leg.qty,
                "price": leg.price if leg.price is not None else 1.0,
            }
            for leg in request.legs
        ]
        result = OrderResult(
            ok=True,
            order_id=order_id,
            env=request.env.value,
            message="mock fill (no OpenD)",
            request=request.as_dict(),
            fills=fills,
        )
        self._orders[order_id] = result
        self.policy.controls.record_open(request.notional)
        self._positions.append(
            {
                "order_id": order_id,
                "underlying": request.underlying,
                "structure_id": request.structure_id,
                "legs": fills,
                "status": "open",
            }
        )
        return result

    def cancel(self, order_id: str) -> dict[str, Any]:
        if order_id not in self._orders:
            return {"ok": False, "message": f"unknown order {order_id}"}
        return {"ok": True, "order_id": order_id, "message": "mock cancel"}

    def positions(self) -> list[dict[str, Any]]:
        return list(self._positions)

    def funds(self) -> dict[str, Any]:
        c = self.policy.controls
        return {
            "source": "mock",
            "allocation": c.allocation,
            "allocated_used": c.allocated_used,
            "power": c.allocation - c.allocated_used,
            "env": self.policy.env.value,
        }


class FutuTradeBackend:
    """Live OpenD trade path. Defaults to SIMULATE via policy."""

    def __init__(
        self,
        policy: TradePolicy | None = None,
        host: str = "127.0.0.1",
        port: int = 11111,
    ):
        self.policy = policy or TradePolicy()
        self.host = host
        self.port = port

    def place(self, request: OrderRequest) -> OrderResult:
        from futu import (
            OpenSecTradeContext,
            OrderType,
            RET_OK,
            TrdEnv,
            TrdMarket,
            TrdSide,
        )

        try:
            self.policy.authorize_open(
                notional=request.notional,
                naked_short=request.naked_short,
            )
        except PolicyError as exc:
            return OrderResult(
                ok=False,
                order_id="",
                env=request.env.value,
                message=exc.message,
                request=request.as_dict(),
            )

        trd_env = TrdEnv.SIMULATE if request.env == TradeEnv.SIMULATE else TrdEnv.REAL
        self.policy.require_simulate_or_unlocked()
        if len(request.legs) != 1:
            # Multi-leg: place sequentially in v1; document upgrade path for combo APIs.
            results = []
            for leg in request.legs:
                single = OrderRequest(
                    underlying=request.underlying,
                    legs=[leg],
                    structure_id=request.structure_id,
                    env=request.env,
                    notional=0.0,
                    naked_short=request.naked_short,
                    client_order_id=f"{request.client_order_id}-{leg.code}",
                )
                results.append(self._place_single(single, trd_env))
            ok = all(r.ok for r in results)
            return OrderResult(
                ok=ok,
                order_id=",".join(r.order_id for r in results if r.order_id),
                env=request.env.value,
                message="multi-leg sequential" if ok else "multi-leg partial failure",
                request=request.as_dict(),
                fills=[f for r in results for f in r.fills],
            )
        return self._place_single(request, trd_env)

    def _place_single(self, request: OrderRequest, trd_env: Any) -> OrderResult:
        from futu import OpenSecTradeContext, OrderType, RET_OK, TrdMarket, TrdSide

        leg = request.legs[0]
        side = TrdSide.BUY if leg.side.upper() == "BUY" else TrdSide.SELL
        price = float(leg.price if leg.price is not None else 0)
        ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.US, host=self.host, port=self.port)
        try:
            ret, data = ctx.place_order(
                price=price,
                qty=leg.qty,
                code=leg.code,
                trd_side=side,
                order_type=OrderType.NORMAL,
                trd_env=trd_env,
            )
            if ret != RET_OK:
                return OrderResult(
                    ok=False,
                    order_id="",
                    env=request.env.value,
                    message=str(data),
                    request=request.as_dict(),
                )
            self.policy.note_order(time.time())
            self.policy.controls.record_open(request.notional)
            order_id = str(data.iloc[0].get("order_id", "")) if hasattr(data, "iloc") else str(data)
            return OrderResult(
                ok=True,
                order_id=order_id,
                env=request.env.value,
                message="submitted",
                request=request.as_dict(),
                fills=[{"code": leg.code, "side": leg.side, "qty": leg.qty, "price": price}],
            )
        finally:
            ctx.close()

    def cancel(self, order_id: str) -> dict[str, Any]:
        from futu import OpenSecTradeContext, RET_OK, TrdEnv, TrdMarket

        trd_env = TrdEnv.SIMULATE if self.policy.env == TradeEnv.SIMULATE else TrdEnv.REAL
        ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.US, host=self.host, port=self.port)
        try:
            ret, data = ctx.modify_order(
                modify_order_op="CANCEL", order_id=order_id, qty=0, price=0, trd_env=trd_env
            )
            return {"ok": ret == RET_OK, "data": str(data), "order_id": order_id}
        finally:
            ctx.close()

    def positions(self) -> list[dict[str, Any]]:
        from futu import OpenSecTradeContext, RET_OK, TrdEnv, TrdMarket

        trd_env = TrdEnv.SIMULATE if self.policy.env == TradeEnv.SIMULATE else TrdEnv.REAL
        ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.US, host=self.host, port=self.port)
        try:
            ret, data = ctx.position_list_query(trd_env=trd_env)
            if ret != RET_OK:
                raise RuntimeError(data)
            return data.to_dict(orient="records") if hasattr(data, "to_dict") else []
        finally:
            ctx.close()

    def funds(self) -> dict[str, Any]:
        from futu import OpenSecTradeContext, RET_OK, TrdEnv, TrdMarket

        trd_env = TrdEnv.SIMULATE if self.policy.env == TradeEnv.SIMULATE else TrdEnv.REAL
        ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.US, host=self.host, port=self.port)
        try:
            ret, data = ctx.accinfo_query(trd_env=trd_env)
            if ret != RET_OK:
                raise RuntimeError(data)
            row = data.iloc[0].to_dict() if hasattr(data, "iloc") else {"raw": str(data)}
            row["source"] = "futu"
            row["env"] = self.policy.env.value
            return row
        finally:
            ctx.close()


def get_trade_backend(
    *,
    prefer_mock: bool | None = None,
    policy: TradePolicy | None = None,
    host: str = "127.0.0.1",
    port: int = 11111,
) -> TradeBackend:
    if prefer_mock is None:
        prefer_mock = os.environ.get("MIOPTION_FUTU_MOCK", "1") == "1"
    policy = policy or TradePolicy()
    if prefer_mock:
        return MockTradeBackend(policy=policy)
    from .opend import connect

    status = connect(host, port, probe_trade=True)
    if not (status.tcp_open and status.futu_importable):
        raise RuntimeError(status.message or "OpenD unavailable; set MIOPTION_FUTU_MOCK=1")
    return FutuTradeBackend(policy=policy, host=host, port=port)
