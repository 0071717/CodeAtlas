#!/usr/bin/env python3
"""Canonical CodeAtlas V2 runner.

Runs the deterministic V2 suite, promotes JSON-compatible legacy `.yaml` outputs
to canonical `.json` outputs, and exposes report/validation helpers.

The restricted-network path assumes MCP is unavailable. The canonical runner can
therefore also build the local no-MCP memory layer: capability-gap audit plus
SQLite read model.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
ATLAS = ROOT / "atlas"
SUITE = ATLAS / "tools" / "codeatlas_v2_suite.py"
DOCTOR = ATLAS / "tools" / "codeatlas_preflight_doctor.py"
GRAPH_REPORT = ATLAS / "tools" / "codeatlas_graph_report.py"
ARTIFACT_VALIDATOR = ATLAS / "tools" / "validate_artifacts.py"
CAPABILITY_AUDIT = ATLAS / "tools" / "codeatlas_capability_audit.py"
SQLITE_READ_MODEL = ATLAS / "tools" / "codeatlas_sqlite_read_model.py"

ARTIFACT_DIRS = [
    "source",
    "index",
    "payloads",
    "bindings",
    "runtime",
    "graph",
    "errors",
    "flows",
    "facts",
    "rules",
    "requirements",
    "testing",
    "knowledge",
    "audit",
    "change",
    "context-packs",
    "visualizer",
]


def run_python(script: Path, args: list[str]) -> int:
    if not script.exists():
        print(f"missing script: {script}", file=sys.stderr)
        return 1
    return subprocess.call([sys.executable, str(script), *args])


def is_json_compatible(path: Path) -> bool:
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True
    except Exception:
        return False


def promote_yaml_json_to_json() -> list[dict[str, Any]]:
    promoted: list[dict[str, Any]] = []
    for rel in ARTIFACT_DIRS:
        root = ATLAS / rel
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.yaml")):
            if not is_json_compatible(path):
                continue
            target = path.with_suffix(".json")
            if not target.exists() or target.read_text(encoding="utf-8") != path.read_text(encoding="utf-8"):
                target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
                promoted.append({"from": str(path), "to": str(target)})
    report = {
        "status": "ok",
        "promoted_count": len(promoted),
        "promoted": promoted,
        "note": "Canonical V2 artifacts should use .json. Legacy .yaml files are retained for backwards compatibility.",
    }
    out = ATLAS / "audit" / "artifact-json-promotion-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return promoted


def run_graph_report() -> int:
    return run_python(GRAPH_REPORT, [])


def run_artifact_validation() -> int:
    return run_python(ARTIFACT_VALIDATOR, [str(ATLAS)])


def run_no_mcp_memory() -> int:
    """Build the local no-MCP memory layer from canonical artifacts."""
    promote_yaml_json_to_json()
    capability_code = run_python(CAPABILITY_AUDIT, [])
    sqlite_code = run_python(SQLITE_READ_MODEL, [])
    promote_yaml_json_to_json()
    return capability_code or sqlite_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Canonical CodeAtlas V2 runner with JSON promotion")
    parser.add_argument(
        "cmd",
        choices=[
            "doctor",
            "init",
            "snapshot",
            "index",
            "graph",
            "semantic-layers",
            "validate",
            "drift-check",
            "visualizer-export",
            "all",
            "promote-json",
            "graph-report",
            "validate-artifacts",
            "capability-audit",
            "sqlite-read-model",
            "no-mcp-memory",
        ],
    )
    args = parser.parse_args()

    if args.cmd == "doctor":
        code = run_python(DOCTOR, [])
        promote_yaml_json_to_json()
        return code
    if args.cmd == "promote-json":
        promoted = promote_yaml_json_to_json()
        print(f"promoted {len(promoted)} JSON-compatible YAML artifacts")
        return 0
    if args.cmd == "graph-report":
        promote_yaml_json_to_json()
        return run_graph_report()
    if args.cmd == "validate-artifacts":
        promote_yaml_json_to_json()
        return run_artifact_validation()
    if args.cmd == "capability-audit":
        promote_yaml_json_to_json()
        code = run_python(CAPABILITY_AUDIT, [])
        promote_yaml_json_to_json()
        return code
    if args.cmd == "sqlite-read-model":
        promote_yaml_json_to_json()
        code = run_python(SQLITE_READ_MODEL, [])
        promote_yaml_json_to_json()
        return code
    if args.cmd == "no-mcp-memory":
        return run_no_mcp_memory()

    code = run_python(SUITE, [args.cmd])
    promoted = promote_yaml_json_to_json()
    print(f"json-promotion {len(promoted)}")
    if args.cmd == "all" and code == 0:
        memory_code = run_no_mcp_memory()
        report_code = run_graph_report()
        validate_code = run_artifact_validation()
        return memory_code or report_code or validate_code
    return code


if __name__ == "__main__":
    raise SystemExit(main())
