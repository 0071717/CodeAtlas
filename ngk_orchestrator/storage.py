from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ngk_framework.base import Workspace

from .models import orchestration_id, read_json, utc_now, write_json, write_yaml


class OrchestrationStore:
    def __init__(self, ws: Workspace) -> None:
        self.ws = ws
        self.root = ws.ngk / "orchestrations"
        self.index_path = self.root / "index.jsonl"

    def create(self, kind: str = "review", request: str = "", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        oid = orchestration_id()
        path = self.path(oid)
        payload = {"schema_version": "1", "orchestration_id": oid, "kind": kind, "request": request, "status": "initialized", "created_at": utc_now(), "metadata": metadata or {}}
        for rel in ("deterministic", "tasks"):
            (path / rel).mkdir(parents=True, exist_ok=True)
        write_json(path / "orchestration.json", payload)
        write_json(path / "conflicts.json", {"schema_version": "1", "conflicts": []})
        write_json(path / "synthesis.json", {"schema_version": "1", "verdict": "pending", "accepted_findings": [], "rejected_findings": [], "conflicts": [], "known_unknowns": [], "recommended_tests": [], "audit": {}})
        (path / "summary.md").write_text("# Orchestration Summary\n\nPending synthesis.\n", encoding="utf-8")
        self.root.mkdir(parents=True, exist_ok=True)
        with self.index_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"orchestration_id": oid, "created_at": payload["created_at"], "kind": kind, "status": payload["status"]}, sort_keys=True) + "\n")
        return payload

    def path(self, oid: str) -> Path:
        return self.root / oid

    def latest_id(self) -> str | None:
        rows = self.list()
        return rows[-1]["orchestration_id"] if rows else None

    def resolve(self, oid: str) -> str:
        if oid == "latest":
            latest = self.latest_id()
            if not latest:
                raise SystemExit("No orchestrations found")
            return latest
        return oid

    def load(self, oid: str) -> dict[str, Any]:
        rid = self.resolve(oid)
        payload = read_json(self.path(rid) / "orchestration.json")
        if not payload:
            raise SystemExit(f"Unknown orchestration: {oid}")
        return payload

    def list(self) -> list[dict[str, Any]]:
        if not self.index_path.exists():
            return []
        rows = []
        for line in self.index_path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
        return rows

    def task_dir(self, oid: str, tid: str) -> Path:
        path = self.path(self.resolve(oid)) / "tasks" / tid
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_task_contract(self, oid: str, tid: str, contract: dict[str, Any]) -> Path:
        path = self.task_dir(oid, tid) / "task-contract.yaml"
        write_yaml(path, contract)
        return path
