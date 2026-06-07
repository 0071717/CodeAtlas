from __future__ import annotations

import json
from typing import Any

from ngk_framework.base import Workspace

from .models import utc_now
from .storage import OrchestrationStore


class EventLog:
    def __init__(self, ws: Workspace, orchestration_id: str) -> None:
        self.ws = ws
        self.store = OrchestrationStore(ws)
        self.oid = self.store.resolve(orchestration_id)
        self.path = self.store.path(self.oid) / "events.jsonl"

    def append(self, event_type: str, **data: Any) -> dict[str, Any]:
        event = {"schema_version": "1", "timestamp": utc_now(), "orchestration_id": self.oid, "event_type": event_type, "data": data}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
        return event

    def read(self, limit: int | None = None) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return rows[-limit:] if limit else rows
