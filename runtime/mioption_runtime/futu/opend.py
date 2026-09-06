"""OpenD connection health and permission probe."""

from __future__ import annotations

import socket
from dataclasses import asdict, dataclass, field
from typing import Any


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 11111


@dataclass
class ConnectionStatus:
    host: str
    port: int
    tcp_open: bool
    futu_importable: bool
    quote_ctx_ok: bool = False
    trade_ctx_ok: bool = False
    message: str = ""
    permissions: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def tcp_reachable(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def futu_available() -> bool:
    try:
        import futu  # noqa: F401

        return True
    except ImportError:
        return False


def connect(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    probe_trade: bool = True,
) -> ConnectionStatus:
    """Probe OpenD without placing orders. Safe for Phase A."""
    status = ConnectionStatus(
        host=host,
        port=port,
        tcp_open=tcp_reachable(host, port),
        futu_importable=futu_available(),
    )
    if not status.futu_importable:
        status.message = "futu-api not installed in this Python environment"
        return status
    if not status.tcp_open:
        status.message = f"OpenD not reachable at {host}:{port}; start and login OpenD first"
        return status

    try:
        from futu import OpenQuoteContext, OpenSecTradeContext, TrdEnv, TrdMarket

        quote_ctx = OpenQuoteContext(host=host, port=port)
        try:
            ret, data = quote_ctx.get_global_state()
            status.quote_ctx_ok = ret == 0
            if ret == 0 and data is not None:
                status.permissions["global_state"] = (
                    data.to_dict() if hasattr(data, "to_dict") else str(data)
                )
            else:
                status.message = f"quote context error: {data}"
        finally:
            quote_ctx.close()

        if probe_trade:
            try:
                trade_ctx = OpenSecTradeContext(
                    filter_trdmarket=TrdMarket.US, host=host, port=port
                )
            except TypeError:
                trade_ctx = OpenSecTradeContext(host=host, port=port)
            try:
                ret, data = trade_ctx.get_acc_list()
                status.trade_ctx_ok = ret == 0
                if ret == 0 and data is not None:
                    status.permissions["accounts"] = (
                        data.to_dict(orient="records")
                        if hasattr(data, "to_dict")
                        else str(data)
                    )
                else:
                    status.message = (status.message + "; " if status.message else "") + f"trade: {data}"
            finally:
                trade_ctx.close()

        if status.quote_ctx_ok and (status.trade_ctx_ok or not probe_trade):
            status.message = status.message or "OpenD connected (SIMULATE path ready)"
    except Exception as exc:  # noqa: BLE001 — surface any OpenD/SDK failure
        status.message = f"OpenD probe failed: {exc}"

    return status


def probe_permissions(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> dict[str, Any]:
    """Phase A helper: connection + high-level permission snapshot."""
    status = connect(host, port, probe_trade=True)
    out = status.as_dict()
    out["trade_env_default"] = "SIMULATE"
    out["notes"] = [
        "App strategy coverage ≠ API entitlement",
        "REAL trading requires explicit unlock in TradePolicy and agent hooks",
        "See knowledge/wiki/meta/Futu OpenAPI integration.md",
    ]
    return out
