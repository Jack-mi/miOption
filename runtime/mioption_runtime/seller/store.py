"""JSON archive under runtime/data/seller/ (gitignored)."""

from __future__ import annotations

import json
import os
import fcntl
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .cards import SellerCard


def default_root() -> Path:
    env = os.environ.get("MIOPTION_SELLER_DIR")
    if env:
        return Path(env)
    mode = "mock" if os.environ.get("MIOPTION_FUTU_MOCK", "1") == "1" else "live"
    return Path(__file__).resolve().parents[2] / "data" / mode / "seller"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class SellerStore:
    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else default_root()
        self.signals = self.root / "signals"
        self.marks = self.root / "marks"
        self.events = self.root / "events"
        self.ledger_path = self.root / "ledger.json"
        for folder in (self.signals, self.marks, self.events):
            folder.mkdir(parents=True, exist_ok=True)
        if not self.ledger_path.is_file():
            self._write_json(self.ledger_path, {"entries": []})

    @contextmanager
    def transaction(self):
        with (self.root / ".lock").open("a") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    def _read_json(self, path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    def save_card(self, card: SellerCard) -> SellerCard:
        if not card.created_at:
            card.created_at = _now()
        card.updated_at = _now()
        self._write_json(self.signals / f"{card.id}.json", card.as_dict())
        return card

    def get_card(self, card_id: str) -> SellerCard | None:
        if not card_id or Path(card_id).name != card_id or "\\" in card_id:
            raise ValueError("invalid card_id")
        path = self.signals / f"{card_id}.json"
        if not path.is_file():
            return None
        return SellerCard.from_dict(self._read_json(path))

    def delete_card(self, card_id: str) -> None:
        path = self.signals / f"{card_id}.json"
        if path.is_file():
            path.unlink()

    def list_cards(self, status: str | None = None) -> list[SellerCard]:
        out: list[SellerCard] = []
        for path in sorted(self.signals.glob("*.json")):
            card = SellerCard.from_dict(self._read_json(path))
            if status and card.status != status:
                continue
            out.append(card)
        return out

    def save_mark(self, card_id: str, verdict: str, note: str = "") -> dict[str, Any]:
        payload = {
            "card_id": card_id,
            "verdict": verdict,
            "note": note,
            "at": _now(),
        }
        self._write_json(self.marks / f"{card_id}.json", payload)
        return payload

    def append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        event = dict(event)
        event.setdefault("at", _now())
        eid = str(event.get("id") or f"{event.get('kind', 'event')}-{uuid4().hex}")
        event["id"] = eid
        self._write_json(self.events / f"{eid}.json", event)
        ledger = self._read_json(self.ledger_path)
        ledger.setdefault("entries", []).append(
            {
                "id": eid,
                "kind": event.get("kind"),
                "card_id": event.get("card_id"),
                "at": event["at"],
            }
        )
        self._write_json(self.ledger_path, ledger)
        return event

    def list_events(self, card_id: str | None = None) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for path in sorted(self.events.glob("*.json")):
            ev = self._read_json(path)
            if card_id and ev.get("card_id") != card_id:
                continue
            out.append(ev)
        return sorted(out, key=lambda event: str(event.get("at") or ""))
