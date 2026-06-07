#!/usr/bin/env python3
"""Canonical CodeAtlas V2 runner.

Runs the deterministic V2 suite, promotes JSON-compatible legacy `.yaml` outputs
into canonical `.json` outputs, records a strict run manifest, and gates derived
read models/context surfaces behind validation.

The restricted-network path assumes MCP is unavailable. The canonical runner can
therefore also build the local no-MCP memory layer: capability-gap audit plus
SQLite read model.
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path.cwd()
ATLAS = ROOT / "atlas"
SUITE = ATLAS / "tools" / "codeatlas_v2_suite.py"
DOCTOR = ATLAS / "tools" / "codeatlas_preflight_doctor.py"
GRAPH_REPORT = ATLAS / "tools" / "codeatlas_graph_report.py"
ARTIFACT_VALIDATOR = ATLAS / "tools" / "validate_artifacts.py"
CAPABILITY_AUDIT = ATLAS / "tools" / "codeatlas_capability_audit.py"
SQLITE_READ_MODEL = ATLAS / "tools" / "codeatlas_sqlite_read_model.py"
CONTEXT_PACK = ATLAS / "tools" / "codeatlas_context_pack.py"
TRUST_ENVELOPE = ATLAS / "tools" / "codeatlas_trust_envelope.py"
RUN_MANIFEST = ATLAS / "audit" / "run-manifest.json"
LEGACY_RUN_MANIFEST = ATLAS / "audit" / "canonical-run-manifest.json"

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


def git_dirty_files() -> list[str]:
    try:
        result = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, text=True, capture_output=True, check=True)
    except Exception:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def git_dirty_worktree() -> bool:
    return bool(git_dirty_files())


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def collect_artifact_paths() -> list[str]:
    paths: list[str] = []
    if not ATLAS.exists():
        return paths
    for rel in ARTIFACT_DIRS:
        root = ATLAS / rel
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".json", ".yaml", ".yml", ".sqlite", ".md"}:
                paths.append(str(path.relative_to(ROOT)))
    return sorted(set(paths))


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
    command: list[str]
    strict: bool
    run_id: str = field(default_factory=lambda: f"run_{uuid.uuid4().hex}")
    started_at: str = field(default_factory=now)
    finished_at: str | None = None
    working_directory: str = field(default_factory=lambda: str(ROOT))
    source_commit: str | None = field(default_factory=lambda: git_commit())
    dirty_files: list[str] = field(default_factory=lambda: git_dirty_files())
    python_version: str = field(default_factory=lambda: sys.version.replace("\n", " "))
    platform: str = field(default_factory=platform.platform)
    tool_versions: dict[str, str] = field(default_factory=lambda: {"python": platform.python_version()})
    input_artifacts: list[str] = field(default_factory=collect_artifact_paths)
    output_artifacts: list[str] = field(default_factory=list)
    validation_status: str = "not_run"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    status: str = "running"
    exit_code: int | None = None
    stopped_on_failure: str | None = None

    @property
    def dirty_worktree(self) -> bool:
        return bool(self.dirty_files)

    def add_error(self, message: str) -> None:
        if message not in self.errors:
            self.errors.append(message)

    def add_warning(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def write(self) -> None:
        payload = {
            "schema_version": "codeatlas.run-manifest.v1",
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "command": self.command,
            "working_directory": self.working_directory,
            "source_commit": self.source_commit,
            "dirty_worktree": self.dirty_worktree,
            "dirty_files": self.dirty_files,
            "python_version": self.python_version,
            "platform": self.platform,
            "tool_versions": self.tool_versions,
            "input_artifacts": self.input_artifacts,
            "output_artifacts": self.output_artifacts,
            "validation_status": self.validation_status,
            "errors": self.errors,
            "warnings": self.warnings,
            "strict": self.strict,
            "status": self.status,
            "exit_code": self.exit_code,
            "stopped_on_failure": self.stopped_on_failure,
            "steps": [step.to_json() for step in self.steps],
        }
        write_json(RUN_MANIFEST, payload)
        # Compatibility for older docs/tools that referenced the original draft path.
        write_json(LEGACY_RUN_MANIFEST, payload)

    def finish(self, exit_code: int) -> int:
        self.exit_code = exit_code
        self.status = "ok" if exit_code == 0 else "error"
        if exit_code != 0 and not self.errors:
            self.add_error(f"canonical run failed with exit code {exit_code}")
        self.finished_at = now()
        self.output_artifacts = collect_artifact_paths()
        self.write()
        return exit_code


class CanonicalRunner:
    def __init__(self, manifest: RunManifest):
        self.manifest = manifest

    def _record_internal(self, name: str, note: str, return_code: int = 0) -> int:
        started = now()
        step = Step(name=name, argv=["<internal>", name], started_at=started, finished_at=now(), return_code=return_code, note=note)
        self.manifest.steps.append(step)
        if return_code and self.manifest.strict and self.manifest.stopped_on_failure is None:
            self.manifest.stopped_on_failure = name
        return return_code

    def run_python(self, name: str, script: Path, args: list[str] | None = None) -> int:
        args = args or []
        argv = [sys.executable, str(script), *args]
        step = Step(name=name, argv=argv, started_at=now())
        self.manifest.steps.append(step)
        if not script.exists():
            step.finished_at = now()
            step.return_code = 1
            step.note = f"missing script: {script}"
            self.manifest.add_error(step.note)
            print(step.note, file=sys.stderr)
            if self.manifest.strict and self.manifest.stopped_on_failure is None:
                self.manifest.stopped_on_failure = name
            return 1
        completed = subprocess.run(argv)
        step.finished_at = now()
        step.return_code = completed.returncode
        if completed.returncode != 0:
            self.manifest.add_error(f"{name} failed with exit code {completed.returncode}")
            if self.manifest.strict and self.manifest.stopped_on_failure is None:
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
        code = self.run_python("validate-artifacts", ARTIFACT_VALIDATOR, args)
        report_path = ATLAS / "audit" / "artifact-validation-report.json"
        if report_path.exists():
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
                self.manifest.validation_status = "passed" if report.get("status") == "ok" and code == 0 else "failed"
                for finding in report.get("findings", []):
                    message = f"{finding.get('severity')}:{finding.get('type')}:{finding.get('path') or finding.get('artifact') or finding.get('record') or ''}"
                    if finding.get("severity") == "error":
                        self.manifest.add_error(message)
                    elif finding.get("severity") == "warning":
                        self.manifest.add_warning(message)
            except Exception as exc:
                self.manifest.validation_status = "failed"
                self.manifest.add_error(f"could not read validation report: {exc}")
        else:
            self.manifest.validation_status = "failed" if code else "not_reported"
            self.manifest.add_warning("validation did not produce atlas/audit/artifact-validation-report.json")
        return code

    def run_context_pack_readiness(self, strict: bool) -> int:
        args = ["ready"]
        if strict:
            args.append("--strict")
        return self.run_python("context-pack-readiness", CONTEXT_PACK, args)

    def run_no_mcp_memory(self) -> int:
        envelope_code = self.run_trust_envelope()
        if self.manifest.strict and envelope_code:
            return envelope_code
        capability_code = self.run_python("capability-audit", CAPABILITY_AUDIT)
        if self.manifest.strict and capability_code:
            return capability_code
        validation_code = self.run_artifact_validation(strict=self.manifest.strict)
        if self.manifest.strict and validation_code:
            return validation_code
        sqlite_args = ["--strict"] if self.manifest.strict else []
        sqlite_code = self.run_python("sqlite-read-model", SQLITE_READ_MODEL, sqlite_args)
        self.promote_yaml_json_to_json()
        return envelope_code or capability_code or validation_code or sqlite_code

    def run_suite_command(self, cmd: str) -> int:
        code = self.run_python(f"suite:{cmd}", SUITE, [cmd])
        promoted = self.promote_yaml_json_to_json()
        print(f"json-promotion {len(promoted)}")
        if cmd in {"semantic-layers", "graph"} and code == 0:
            trust_code = self.run_trust_envelope()
            return trust_code or code
        return code

    def _strict_step(self, name: str, func: Callable[[], int]) -> int:
        code = func()
        if code and self.manifest.stopped_on_failure is None:
            self.manifest.stopped_on_failure = name
        return code

    def run_all_strict(self) -> int:
        strict_steps: list[tuple[str, Callable[[], int]]] = [
            ("source snapshot:init", lambda: self.run_python("suite:init", SUITE, ["init"])),
            ("source snapshot:snapshot", lambda: self.run_python("suite:snapshot", SUITE, ["snapshot"])),
            ("provenance manifest", lambda: self._record_internal("provenance-manifest", "run manifest records commit, dirty state, command, and artifact inputs")),
            ("deterministic extractors:index", lambda: self.run_python("suite:index", SUITE, ["index"])),
            ("deterministic extractors:graph", lambda: self.run_python("suite:graph", SUITE, ["graph"])),
            ("deterministic extractors:semantic-layers", lambda: self.run_python("suite:semantic-layers", SUITE, ["semantic-layers"])),
            ("trust envelope", self.run_trust_envelope),
            ("capability audit", lambda: self.run_python("capability-audit", CAPABILITY_AUDIT)),
            ("artifact validation:suite", lambda: self.run_python("suite:validate", SUITE, ["validate"])),
            ("artifact validation:strict", lambda: self.run_artifact_validation(strict=True)),
            ("stale drift validation", lambda: self.run_python("suite:drift-check", SUITE, ["drift-check"])),
            ("promotion of verified findings", lambda: (self.promote_yaml_json_to_json() and 0)),
            ("sqlite read model", lambda: self.run_python("sqlite-read-model", SQLITE_READ_MODEL, ["--strict"])),
            ("context pack readiness", lambda: self.run_context_pack_readiness(strict=True)),
            ("graph report export", self.run_graph_report),
            ("final audit report", lambda: self.run_artifact_validation(strict=True)),
        ]
        for name, func in strict_steps:
            code = self._strict_step(name, func)
            if code:
                return code
        return 0

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
    parser = argparse.ArgumentParser(description="Canonical CodeAtlas V2 runner with strict fail-closed validation")
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
    parser.add_argument("--strict", action="store_true", help="Fail closed and write atlas/audit/run-manifest.json")
    args = parser.parse_args()

    manifest = RunManifest(command=sys.argv[:], strict=args.strict)
    runner = CanonicalRunner(manifest)

    try:
        if args.cmd == "doctor":
            code = runner.run_python("doctor", DOCTOR)
            runner.promote_yaml_json_to_json()
            if args.strict and code == 0:
                trust_code = runner.run_trust_envelope()
                if trust_code:
                    return manifest.finish(trust_code)
                validation_code = runner.run_artifact_validation(strict=True)
                return manifest.finish(validation_code)
            return manifest.finish(code)
        if args.cmd == "promote-json":
            promoted = runner.promote_yaml_json_to_json()
            print(f"promoted {len(promoted)} JSON-compatible YAML artifacts")
            return manifest.finish(0)
        if args.cmd == "trust-envelope":
            return manifest.finish(runner.run_trust_envelope())
        if args.cmd == "graph-report":
            if args.strict:
                validation_code = runner.run_artifact_validation(strict=True)
                if validation_code:
                    return manifest.finish(validation_code)
            return manifest.finish(runner.run_graph_report())
        if args.cmd == "validate-artifacts":
            if args.strict:
                trust_code = runner.run_trust_envelope()
                if trust_code:
                    return manifest.finish(trust_code)
            return manifest.finish(runner.run_artifact_validation(strict=args.strict))
        if args.cmd == "capability-audit":
            code = runner.run_trust_envelope()
            if args.strict and code:
                return manifest.finish(code)
            audit_code = runner.run_python("capability-audit", CAPABILITY_AUDIT)
            runner.promote_yaml_json_to_json()
            return manifest.finish(code or audit_code)
        if args.cmd == "sqlite-read-model":
            if args.strict:
                validation_code = runner.run_artifact_validation(strict=True)
                if validation_code:
                    return manifest.finish(validation_code)
            sqlite_args = ["--strict"] if args.strict else []
            sqlite_code = runner.run_python("sqlite-read-model", SQLITE_READ_MODEL, sqlite_args)
            runner.promote_yaml_json_to_json()
            return manifest.finish(sqlite_code)
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
        manifest.add_error("interrupted")
        return manifest.finish(130)
    except Exception as exc:
        manifest.add_error(f"unhandled exception: {exc}")
        return manifest.finish(1)


if __name__ == "__main__":
    raise SystemExit(main())
