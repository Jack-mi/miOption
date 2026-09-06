"""Bot engine: Trigger → Conditions → Actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..futu.policy import TradeEnv, TradePolicy
from ..futu.trade import TradeBackend, get_trade_backend
from . import exit_monitor
from .actions import run_action
from .conditions import eval_all
from .models import Action, Condition, ExitRules, Role, Trigger
from .triggers import matches


@dataclass
class Automation:
    id: str
    role: Role
    trigger: Trigger
    conditions: list[Condition] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    enabled: bool = True


@dataclass
class BotState:
    managed: dict[str, Any] = field(default_factory=lambda: {"positions": {}, "tags": []})
    last_run: dict[str, Any] | None = None


class BotEngine:
    def __init__(
        self,
        automations: list[Automation] | None = None,
        *,
        trade: TradeBackend | None = None,
        policy: TradePolicy | None = None,
        env: TradeEnv = TradeEnv.SIMULATE,
        prefer_mock: bool | None = None,
    ):
        self.automations = list(automations or [])
        self.policy = policy or TradePolicy(env=env)
        self.env = env
        self.trade = trade or get_trade_backend(prefer_mock=prefer_mock, policy=self.policy)
        self.state = BotState()

    def register(self, automation: Automation) -> None:
        self.automations.append(automation)

    def run(
        self,
        kind: str,
        *,
        webhook_id: str | None = None,
        event: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ctx = dict(context or {})
        ctx.setdefault("position", {
            "open_count": self.policy.controls.open_positions,
            "opens_today": self.policy.controls.opens_today,
        })
        runs = []
        for auto in self.automations:
            if not auto.enabled:
                continue
            if not matches(auto.trigger, kind, webhook_id=webhook_id, event=event):
                continue
            # Scanners refuse opens when capped (pre-check); monitors may still close
            if auto.role == "scanner":
                try:
                    self.policy.controls.check_open(0.0)
                except Exception as exc:  # PolicyError
                    runs.append(
                        {
                            "automation_id": auto.id,
                            "skipped": True,
                            "reason": str(exc),
                        }
                    )
                    continue
            ok, details = eval_all(auto.conditions, ctx)
            action_results = []
            if ok:
                for action in auto.actions:
                    action_results.append(
                        run_action(action, self.trade, managed=self.state.managed, env=self.env)
                    )
            runs.append(
                {
                    "automation_id": auto.id,
                    "role": auto.role,
                    "conditions_ok": ok,
                    "condition_details": details,
                    "actions": action_results,
                }
            )
        result = {"ok": True, "trigger": kind, "webhook_id": webhook_id, "runs": runs}
        self.state.last_run = result
        return result

    def monitor_tick(self, mark_pnl=None) -> list[dict[str, Any]]:
        return exit_monitor.tick(
            self.state.managed,
            self.trade,
            env=self.env,
            mark_pnl=mark_pnl,
        )


def demo_automation(webhook_id: str = "demo-hook") -> Automation:
    """Minimal scanner: webhook → underlying last > 0 → open mock long call."""
    return Automation(
        id="demo-long-call",
        role="scanner",
        trigger=Trigger(kind="webhook", webhook_id=webhook_id),
        conditions=[
            Condition(family="stock", name="stock.last", op="gt", value=0),
        ],
        actions=[
            Action(
                kind="open_position",
                structure_id="long_call",
                underlying="US.SPY",
                notional=100.0,
                legs=[
                    {
                        "code": "US.SPY240119C500000",
                        "side": "BUY",
                        "qty": 1,
                        "price": 1.25,
                        "option_type": "CALL",
                    }
                ],
                exit_rules=ExitRules(profit_take_pct=50.0, stop_loss_pct=-50.0),
            )
        ],
    )
