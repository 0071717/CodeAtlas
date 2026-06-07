from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import yaml

from .base import Workspace, load_yaml_or_json, read_jsonl
from .store import AtlasStore

def artifact_rows(ws: Workspace, names: Iterable[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    wanted = {name.lower() for name in names}
    for root in [ws.atlas, ws.atlas / "contracts", ws.atlas / "indexes"]:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            lower = path.name.lower()
            if not any(name in lower for name in wanted):
                continue
            try:
                if path.suffix == ".jsonl":
                    content: Any = read_jsonl(path)
                else:
                    content = load_yaml_or_json(path) if path.suffix in {".json", ".yaml", ".yml"} else path.read_text(encoding="utf-8", errors="replace")
            except (OSError, json.JSONDecodeError, yaml.YAMLError):
                continue
            rows.append({"path": path.relative_to(ws.atlas).as_posix(), "content": content})
    return rows


def fact_ids_for_contract_query(ws: Workspace, query: str) -> list[str]:
    return [row["fact_id"] for row in AtlasStore(ws).search_facts(query, limit=10)]


def contract_check(ws: Workspace, kind: str) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    gaps: list[str] = []
    if kind in {"check", "api-ui"}:
        openapi = artifact_rows(ws, ["openapi"])
        clients = artifact_rows(ws, ["api_client_calls", "api-client", "client_calls"])
        hooks = artifact_rows(ws, ["query_hooks", "query-hooks"])
        if not openapi:
            gaps.append("openapi.json artifact is missing")
        if not clients:
            gaps.append("TypeScript api_client_calls/client artifact is missing")
        if not hooks:
            gaps.append("query_hooks artifact is missing")
        status = "pass" if openapi and (clients or hooks) else "warn"
        checks.append({
            "check": "api-ui",
            "status": status,
            "evidence": [row["path"] for row in [*openapi, *clients, *hooks]],
            "affected_facts": fact_ids_for_contract_query(ws, "api ui hook client route endpoint"),
            "suggested_fixes": [] if status == "pass" else ["Generate Atlas openapi.json plus TypeScript client/query hook artifacts before enforcing API/UI contract checks."],
        })
    if kind in {"check", "data"}:
        models = artifact_rows(ws, ["pydantic", "model"])
        fields = artifact_rows(ws, ["opensearch", "index", "field"])
        if not models:
            gaps.append("pydantic model artifact is missing")
        if not fields:
            gaps.append("opensearch index/field artifact is missing")
        status = "pass" if models and fields else "warn"
        checks.append({
            "check": "data",
            "status": status,
            "evidence": [row["path"] for row in [*models, *fields]],
            "affected_facts": fact_ids_for_contract_query(ws, "data model service field opensearch"),
            "suggested_fixes": [] if status == "pass" else ["Generate Atlas pydantic model and OpenSearch index/field artifacts before enforcing data contract checks."],
        })
    overall = "fail" if any(c["status"] == "fail" for c in checks) else "warn" if gaps or any(c["status"] == "warn" for c in checks) else "pass"
    return {"status": overall, "checks": checks, "capability_gaps": sorted(set(gaps))}


def print_contract_report(report: dict[str, Any]) -> None:
    print(f"Contract status: {report['status']}")
    for check in report.get("checks", []):
        print(f"- {check['check']}: {check['status']}")
        for ev in check.get("evidence", []):
            print(f"  evidence: {ev}")
        for fact_id in check.get("affected_facts", []):
            print(f"  fact: {fact_id}")
        for fix in check.get("suggested_fixes", []):
            print(f"  fix: {fix}")
    if report.get("capability_gaps"):
        print("Capability gaps:")
        for gap in report["capability_gaps"]:
            print(f"- {gap}")


def cmd_contract(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    report = contract_check(ws, args.contract_cmd)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_contract_report(report)


