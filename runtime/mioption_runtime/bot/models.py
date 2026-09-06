"""Bot DSL primitives."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


TriggerKind = Literal["schedule", "webhook", "resultant", "agent", "button"]
ConditionFamily = Literal["stock", "opportunity", "indicator", "position"]
ActionKind = Literal["open_position", "close_position", "update_exit_rules", "tag"]
Role = Literal["scanner", "monitor"]


@dataclass
class Trigger:
    kind: TriggerKind
    webhook_id: str | None = None
    cron: str | None = None
    event: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Condition:
    family: ConditionFamily
    name: str
    op: Literal["gt", "gte", "lt", "lte", "eq", "exists"] = "gt"
    value: Any = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExitRules:
    profit_take_pct: float | None = 50.0
    stop_loss_pct: float | None = -100.0
    max_dte_remaining: int | None = None
    enabled: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Action:
    kind: ActionKind
    structure_id: str | None = None
    underlying: str | None = None
    legs: list[dict[str, Any]] = field(default_factory=list)
    notional: float = 0.0
    naked_short: bool = False
    exit_rules: ExitRules | None = None
    tag: str | None = None
    position_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d
