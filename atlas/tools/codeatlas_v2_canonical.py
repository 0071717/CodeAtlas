#!/usr/bin/env python3
"""Canonical CodeAtlas V2 runner.

Runs the existing deterministic V2 suite, then promotes JSON-compatible `.yaml`
outputs to canonical `.json` outputs so downstream tools can stop depending on
faux-YAML. This wrapper is intentionally small and safe for pre-transfer use.
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Canonical CodeAtlas V2 runner with JSON promotion")
    parser.add_argument("cmd", choices=["doctor", "init", "snapshot", "index", "graph", "semantic-layers", "validate", "drift-check", "visualizer-export", "all", "promote-json"])
    args = parser.parse_args()

    if args.cmd == "doctor":
        code = run_python(DOCTOR, [])
        promote_yaml_json_to_json()
        return code
    if args.cmd == "promote-json":
        promoted = promote_yaml_json_to_json()
        print(f"promoted {len(promoted)} JSON-compatible YAML artifacts")
        return 0

    code = run_python(SUITE, [args.cmd])
    promoted = promote_yaml_json_to_json()
    print(f"json-promotion {len(promoted)}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
