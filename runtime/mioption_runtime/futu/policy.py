"""Hard gates before any open order (learned Global Controls shape)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TradeEnv(str, Enum):
    SIMULATE = "SIMULATE"
    REAL = "REAL"


class PolicyError(RuntimeError):
    """Raised when a trade would violate policy; no order is sent."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

    def as_dict(self) -> dict[str, Any]:
        return {"ok": False, "error": self.code, "message": self.message}


@dataclass
class GlobalControls:
    allocation: float = 10_000.0
    daily_position_limit: int = 3
    max_position_limit: int = 5
    opens_today: int = 0
    open_positions: int = 0
    allocated_used: float = 0.0

    def check_open(self, notional: float = 0.0) -> None:
        if self.open_positions >= self.max_position_limit:
            raise PolicyError(
                "max_position_limit",
                f"open positions {self.open_positions} >= max {self.max_position_limit}",
            )
        if self.opens_today >= self.daily_position_limit:
            raise PolicyError(
                "daily_position_limit",
                f"opens today {self.opens_today} >= daily limit {self.daily_position_limit}",
            )
        if self.allocated_used + notional > self.allocation:
            raise PolicyError(
                "allocation",
                f"used {self.allocated_used} + {notional} exceeds allocation {self.allocation}",
            )

    def record_open(self, notional: float = 0.0) -> None:
        self.opens_today += 1
        self.open_positions += 1
        self.allocated_used += notional

    def record_close(self, notional: float = 0.0) -> None:
        self.open_positions = max(0, self.open_positions - 1)
        self.allocated_used = max(0.0, self.allocated_used - notional)


@dataclass
class TradePolicy:
    """Default-safe trade policy: SIMULATE only unless explicitly unlocked."""

    env: TradeEnv = TradeEnv.SIMULATE
    real_unlocked: bool = False
    allow_naked_short: bool = False
    controls: GlobalControls = field(default_factory=GlobalControls)
    order_burst: list[float] = field(default_factory=list)
    max_orders_per_30s: int = 15

    def require_simulate_or_unlocked(self) -> None:
        if self.env == TradeEnv.REAL and not self.real_unlocked:
            raise PolicyError(
                "real_locked",
                "REAL environment blocked until explicit unlock and second confirmation",
            )

    def check_rate_limit(self, now: float) -> None:
        window = [t for t in self.order_burst if now - t <= 30.0]
        self.order_burst = window
        if len(window) >= self.max_orders_per_30s:
            raise PolicyError(
                "rate_limit",
                f"order burst {len(window)} in 30s exceeds {self.max_orders_per_30s}",
            )

    def note_order(self, now: float) -> None:
        self.order_burst.append(now)

    def authorize_open(
        self,
        *,
        notional: float = 0.0,
        naked_short: bool = False,
        now: float | None = None,
    ) -> None:
        import time

        self.require_simulate_or_unlocked()
        if naked_short and not self.allow_naked_short:
            raise PolicyError("naked_short_blocked", "naked short opens are disabled by policy")
        self.controls.check_open(notional)
        self.check_rate_limit(time.time() if now is None else now)
