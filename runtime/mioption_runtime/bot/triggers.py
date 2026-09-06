"""Trigger matching helpers."""

from __future__ import annotations

from .models import Trigger


def matches(trigger: Trigger, kind: str, *, webhook_id: str | None = None, event: str | None = None) -> bool:
    if trigger.kind != kind:
        return False
    if kind == "webhook":
        return bool(trigger.webhook_id) and trigger.webhook_id == webhook_id
    if kind == "resultant":
        return trigger.event == event or trigger.event is None
    return True
