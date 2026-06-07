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
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
TRUST_ENVELOPE = ATLAS / "tools" / "codeatlas_trust_envelope.py"
RUN_MANIFEST = ATLAS / "audit" / "canonical-run-manifest.json"

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

PASSTHROUGH_SUITE_COMMANDS = {
    "init",
    "snapshot",
    "index",
    "graph",
    "semantic-layers",
    "validate",
    "drift-check",
    "visualizer-export",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_commit() -> str | None:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True)
    except Exception:
        return None
    return result.stdout.strip() or None


def git_dirty() -> bool | None:
    try:
        result = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, text=True, capture_output=True, check=True)
    except Exception:
        return None
    return bool(result.stdout.strip())


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@dataclass
class Step:
    name: str
    argv: list[str]
    started_at: str
    finished_at: str | None = None
    return_code: int | None = None
    skipped: bool = False
    note: str | None = None

    def to_json(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "argv": self.argv,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "return_code": self.return_code,
            "status": "skipped" if self.skipped else ("ok" if self.return_code == 0 else "error"),
        }
        if self.note:
            data["note"] = self.note
        return data


@dataclass
class RunManifest:
    command: str
    strict: bool
    started_at: str = field(default_factory=now)
    finished_at: str | None = None
    source_commit: str | None = field(default_factory=git_commit)
    dirty_worktree: bool | None = field(default_factory=git_dirty)
    steps: list[Step] = field(default_factory=list)
    status: str = "running"
    exit_code: int | None = None
    stopped_on_failure: str | None = None

    def write(self) -> None:
        write_json(
            RUN_MANIFEST,
            {
                "schema_version": "phase00.run_manifest.v1",
                "artifact_kind": "canonical_run_manifest",
                "generated_at": self.finished_at or now(),
                "command": self.command,
                "strict": self.strict,
                "source_commit": self.source_commit,
                "dirty_worktree": self.dirty_worktree,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "status": self.status,
                "exit_code": self.exit_code,
                "stopped_on_failure": self.stopped_on_failure,
                "steps": [step.to_json() for step in self.steps],
            },
        )

    def finish(self, exit_code: int) -> int:
        self.exit_code = exit_code
        self.status = "ok" if exit_code == 0 else "error"
        self.finished_at = now()
        self.write()
        return exit_code


class CanonicalRunner:
    def __init__(self, manifest: RunManifest):
        self.manifest = manifest

    def run_python(self, name: str, script: Path, args: list[str] | None = None) -> int:
        args = args or []
        argv = [sys.executable, str(script), *args]
        step = Step(name=name, argv=argv, started_at=now())
        self.manifest.steps.append(step)
        if not script.exists():
            step.finished_at = now()
            step.return_code = 1
            step.note = f"missing script: {script}"
            print(step.note, file=sys.stderr)
            return 1
        completed = subprocess.run(argv)
        step.finished_at = now()
        step.return_code = completed.returncode
        if self.manifest.strict and completed.returncode != 0 and self.manifest.stopped_on_failure is None:
            self.manifest.stopped_on_failure = name
        return completed.returncode

    def promote_yaml_json_to_json(self) -> list[dict[str, Any]]:
        promoted = promote_yaml_json_to_json()
        self.manifest.steps.append(
            Step(
                name="promote-json",
                argv=["<internal>", "promote_yaml_json_to_json"],
                started_at=now(),
                finished_at=now(),
                return_code=0,
                note=f"promoted {len(promoted)} JSON-compatible YAML artifacts",
            )
        )
        return promoted

    def run_trust_envelope(self) -> int:
        self.promote_yaml_json_to_json()
        code = self.run_python("trust-envelope", TRUST_ENVELOPE)
        self.promote_yaml_json_to_json()
        return code

    def run_graph_report(self) -> int:
        return self.run_python("graph-report", GRAPH_REPORT)

    def run_artifact_validation(self, strict: bool = False) -> int:
        args = [str(ATLAS)]
        if strict:
            args.append("--strict")
        return self.run_python("validate-artifacts", ARTIFACT_VALIDATOR, args)

    def run_no_mcp_memory(self) -> int:
        envelope_code = self.run_trust_envelope()
        if self.manifest.strict and envelope_code:
            return envelope_code
        capability_code = self.run_python("capability-audit", CAPABILITY_AUDIT)
        if self.manifest.strict and capability_code:
            return capability_code
        sqlite_code = self.run_python("sqlite-read-model", SQLITE_READ_MODEL)
        self.promote_yaml_json_to_json()
        return envelope_code or capability_code or sqlite_code

    def run_suite_command(self, cmd: str) -> int:
        code = self.run_python(f"suite:{cmd}", SUITE, [cmd])
        promoted = self.promote_yaml_json_to_json()
        print(f"json-promotion {len(promoted)}")
        if cmd in {"semantic-layers", "graph"} and code == 0:
            trust_code = self.run_trust_envelope()
            return trust_code or code
        return code

    def run_all_strict(self) -> int:
        for cmd in ["init", "snapshot", "index", "graph", "semantic-layers", "validate", "visualizer-export"]:
            code = self.run_suite_command(cmd)
            if code:
                return code
        memory_code = self.run_no_mcp_memory()
        if memory_code:
            return memory_code
        report_code = self.run_graph_report()
        if report_code:
            return report_code
        return self.run_artifact_validation(strict=True)

    def run_all_legacy_order(self) -> int:
        code = self.run_python("suite:all", SUITE, ["all"])
        promoted = self.promote_yaml_json_to_json()
        print(f"json-promotion {len(promoted)}")
        if code == 0:
            trust_code = self.run_trust_envelope()
            if trust_code:
                return trust_code
            memory_code = self.run_no_mcp_memory()
            report_code = self.run_graph_report()
            validate_code = self.run_artifact_validation(strict=False)
            return memory_code or report_code or validate_code
        return code


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
            "trust-envelope",
            "graph-report",
            "validate-artifacts",
            "capability-audit",
            "sqlite-read-model",
            "no-mcp-memory",
        ],
    )
    parser.add_argument("--strict", action="store_true", help="Fail closed and record the exact canonical run order in atlas/audit/canonical-run-manifest.json")
    args = parser.parse_args()

    manifest = RunManifest(command=args.cmd, strict=args.strict)
    runner = CanonicalRunner(manifest)

    try:
        if args.cmd == "doctor":
            code = runner.run_python("doctor", DOCTOR)
            runner.promote_yaml_json_to_json()
            return manifest.finish(code)
        if args.cmd == "promote-json":
            promoted = runner.promote_yaml_json_to_json()
            print(f"promoted {len(promoted)} JSON-compatible YAML artifacts")
            return manifest.finish(0)
        if args.cmd == "trust-envelope":
            return manifest.finish(runner.run_trust_envelope())
        if args.cmd == "graph-report":
            code = runner.run_trust_envelope()
            if args.strict and code:
                return manifest.finish(code)
            return manifest.finish(code or runner.run_graph_report())
        if args.cmd == "validate-artifacts":
            code = runner.run_trust_envelope()
            if args.strict and code:
                return manifest.finish(code)
            return manifest.finish(code or runner.run_artifact_validation(strict=args.strict))
        if args.cmd == "capability-audit":
            code = runner.run_trust_envelope()
            if args.strict and code:
                return manifest.finish(code)
            audit_code = runner.run_python("capability-audit", CAPABILITY_AUDIT)
            runner.promote_yaml_json_to_json()
            return manifest.finish(code or audit_code)
        if args.cmd == "sqlite-read-model":
            code = runner.run_trust_envelope()
            if args.strict and code:
                return manifest.finish(code)
            sqlite_code = runner.run_python("sqlite-read-model", SQLITE_READ_MODEL)
            runner.promote_yaml_json_to_json()
            return manifest.finish(code or sqlite_code)
        if args.cmd == "no-mcp-memory":
            return manifest.finish(runner.run_no_mcp_memory())
        if args.cmd == "all" and args.strict:
            return manifest.finish(runner.run_all_strict())
        if args.cmd == "all":
            return manifest.finish(runner.run_all_legacy_order())
        if args.cmd in PASSTHROUGH_SUITE_COMMANDS:
            return manifest.finish(runner.run_suite_command(args.cmd))
        return manifest.finish(1)
    except KeyboardInterrupt:
        manifest.stopped_on_failure = "keyboard_interrupt"
        return manifest.finish(130)


if __name__ == "__main__":
    raise SystemExit(main())
