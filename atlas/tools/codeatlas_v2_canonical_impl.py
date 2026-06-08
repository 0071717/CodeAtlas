#!/usr/bin/env python3
"""Implementation module for the strict canonical CodeAtlas V2 runner."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from codeatlas_artifact_contract import (
    attach_artifact_envelope,
    module_version,
    now,
    sha256_json,
    source_descriptor,
    validation_descriptor,
)

ROOT = Path.cwd()
ATLAS = ROOT / "atlas"
SUITE = ATLAS / "tools" / "codeatlas_v2_suite.py"
DOCTOR = ATLAS / "tools" / "codeatlas_preflight_doctor.py"
GRAPH_REPORT = ATLAS / "tools" / "codeatlas_graph_report.py"
ARTIFACT_VALIDATOR = ATLAS / "tools" / "validate_artifacts.py"
CAPABILITY_AUDIT = ATLAS / "tools" / "codeatlas_capability_audit.py"
SQLITE_READ_MODEL = ATLAS / "tools" / "codeatlas_sqlite_read_model.py"
TRUST_ENVELOPE = ATLAS / "tools" / "codeatlas_trust_envelope.py"
RUNNER_ID = "codeatlas_v2_canonical.py"
RUNNER_VERSION = module_version(Path(__file__), prefix="1")

ARTIFACT_DIRS = [
    "source", "index", "payloads", "bindings", "runtime", "graph", "errors",
    "flows", "facts", "rules", "requirements", "testing", "knowledge",
    "audit", "change", "context-packs", "visualizer",
]


class RunManifest:
    def __init__(self, requested_command: str, strict: bool, argv: list[str]) -> None:
        self.started_monotonic = time.monotonic()
        self.path = ATLAS / "audit" / "run-manifest.json"
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self.steps: list[dict[str, Any]] = []
        self.started_at = now()
        self.source = source_descriptor(root=ROOT, file_manifest_hash=self._existing_file_manifest_hash())
        self.doc: dict[str, Any] = attach_artifact_envelope(
            {
                "schema_version": "1",
                "artifact_id": "codeatlas.run_manifest.current",
                "artifact_kind": "run_manifest",
                "generated_at": self.started_at,
                "generator": {"id": RUNNER_ID, "version": RUNNER_VERSION, "command": " ".join(argv)},
                "source": self.source,
                "validation": validation_descriptor(status="unknown", validator=RUNNER_ID),
                "data": {
                    "requested_command": requested_command,
                    "strict": strict,
                    "argv": argv,
                    "root": str(ROOT),
                    "steps": self.steps,
                    "exit_code": None,
                    "status": "running",
                },
            },
            stem="audit/run-manifest",
            artifact_kind="run_manifest",
            generator_id=RUNNER_ID,
            generator_version=RUNNER_VERSION,
            generator_command=" ".join(argv),
            source=self.source,
            validation=validation_descriptor(status="unknown", validator=RUNNER_ID),
            data_keys=["data"],
        )
        self.write()

    def _existing_file_manifest_hash(self) -> str | None:
        for path in [ATLAS / "index" / "file-index.json", ATLAS / "index" / "file-index.yaml"]:
            if path.exists():
                try:
                    return sha256_json(json.loads(path.read_text(encoding="utf-8")))
                except Exception:
                    return None
        return None

    def write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _sync(self) -> None:
        status = "error" if self.errors else "running"
        self.doc["validation"] = validation_descriptor(status=status, validator=RUNNER_ID, errors=self.errors, warnings=self.warnings)
        self.doc["artifact_envelope"]["validation"] = self.doc["validation"]
        self.doc["data"]["steps"] = self.steps
        self.doc["data"]["status"] = status
        self.write()

    def record_internal_step(self, name: str, details: dict[str, Any] | None = None, exit_code: int = 0) -> int:
        step = {
            "name": name,
            "kind": "internal",
            "command": None,
            "started_at": now(),
            "ended_at": now(),
            "duration_ms": 0,
            "exit_code": exit_code,
            "status": "ok" if exit_code == 0 else "error",
            "details": details or {},
        }
        self.steps.append(step)
        if exit_code:
            self.errors.append({"step": name, "exit_code": exit_code, "details": details or {}})
        self._sync()
        return exit_code

    def run_step(self, name: str, argv: list[str]) -> int:
        started_at = now()
        started = time.monotonic()
        step: dict[str, Any] = {
            "name": name,
            "kind": "subprocess",
            "command": argv,
            "started_at": started_at,
            "ended_at": None,
            "duration_ms": None,
            "exit_code": None,
            "status": "running",
        }
        self.steps.append(step)
        self._sync()
        try:
            code = int(subprocess.call(argv))
            step.update({"ended_at": now(), "duration_ms": int((time.monotonic() - started) * 1000), "exit_code": code, "status": "ok" if code == 0 else "error"})
        except Exception as exc:
            code = 1
            step.update({"ended_at": now(), "duration_ms": int((time.monotonic() - started) * 1000), "exit_code": code, "status": "error", "error": str(exc)})
        if code:
            self.errors.append({"step": name, "command": argv, "exit_code": code})
        self._sync()
        return code

    def finish(self, exit_code: int) -> None:
        status = "ok" if exit_code == 0 and not self.errors else "error"
        ended_at = now()
        self.doc["validation"] = validation_descriptor(status=status, validator=RUNNER_ID, errors=self.errors, warnings=self.warnings, validated_at=ended_at)
        self.doc["artifact_envelope"]["validation"] = self.doc["validation"]
        self.doc["data"].update({"status": status, "exit_code": exit_code, "ended_at": ended_at, "duration_ms": int((time.monotonic() - self.started_monotonic) * 1000), "steps": self.steps})
        self.write()


def run_python(script: Path, args: list[str], manifest: RunManifest | None = None, name: str | None = None) -> int:
    step_name = name or script.stem
    if not script.exists():
        message = f"missing script: {script}"
        print(message, file=sys.stderr)
        if manifest is not None:
            return manifest.record_internal_step(step_name, {"error": message, "script": str(script)}, exit_code=1)
        return 1
    argv = [sys.executable, str(script), *args]
    if manifest is not None:
        return manifest.run_step(step_name, argv)
    return subprocess.call(argv)


def is_json_compatible(path: Path) -> bool:
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True
    except Exception:
        return False


def promote_yaml_json_to_json(manifest: RunManifest | None = None) -> list[dict[str, Any]]:
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
    report = {"status": "ok", "promoted_count": len(promoted), "promoted": promoted, "note": "Canonical V2 artifacts should use .json. Legacy .yaml files are retained for backwards compatibility."}
    out = ATLAS / "audit" / "artifact-json-promotion-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if manifest is not None:
        manifest.record_internal_step("promote-json", {"promoted_count": len(promoted), "promoted": promoted})
    return promoted


def run_trust_envelope(manifest: RunManifest | None = None) -> int:
    promote_yaml_json_to_json(manifest)
    code = run_python(TRUST_ENVELOPE, [], manifest, name="trust-envelope")
    if code:
        return code
    promote_yaml_json_to_json(manifest)
    return 0


def run_trust_verify(strict: bool = False, manifest: RunManifest | None = None) -> int:
    args = ["--mode", "verify"]
    if strict:
        args.append("--strict")
    code = run_python(TRUST_ENVELOPE, args, manifest, name="verify")
    if code:
        return code
    promote_yaml_json_to_json(manifest)
    return 0


def run_graph_report(manifest: RunManifest | None = None) -> int:
    return run_python(GRAPH_REPORT, [], manifest, name="graph-report")


def run_artifact_validation(strict: bool = False, manifest: RunManifest | None = None) -> int:
    extra = ["--strict"] if strict else []
    return run_python(ARTIFACT_VALIDATOR, [str(ATLAS), *extra], manifest, name="validate-artifacts")


def run_no_mcp_memory(manifest: RunManifest | None = None, ensure_envelope: bool = True) -> int:
    if ensure_envelope:
        code = run_trust_envelope(manifest)
        if code:
            return code
    for script, name in [(CAPABILITY_AUDIT, "capability-audit"), (SQLITE_READ_MODEL, "sqlite-read-model")]:
        code = run_python(script, [], manifest, name=name)
        if code:
            return code
    promote_yaml_json_to_json(manifest)
    return 0


def run_dispatch(args: argparse.Namespace, manifest: RunManifest) -> int:
    if args.cmd == "doctor":
        code = run_python(DOCTOR, [], manifest, name="doctor")
        if code:
            return code
        promote_yaml_json_to_json(manifest)
        if args.strict:
            code = run_trust_envelope(manifest)
            if code:
                return code
            return run_artifact_validation(strict=True, manifest=manifest)
        return 0
    if args.cmd == "promote-json":
        promoted = promote_yaml_json_to_json(manifest)
        print(f"promoted {len(promoted)} JSON-compatible YAML artifacts")
        return 0
    if args.cmd == "trust-envelope":
        return run_trust_envelope(manifest)
    if args.cmd == "verify":
        return run_trust_verify(strict=args.strict, manifest=manifest)
    if args.cmd == "graph-report":
        code = run_trust_envelope(manifest)
        if code:
            return code
        return run_graph_report(manifest)
    if args.cmd == "validate-artifacts":
        code = run_trust_envelope(manifest)
        if code:
            return code
        return run_artifact_validation(strict=args.strict, manifest=manifest)
    if args.cmd == "capability-audit":
        code = run_trust_envelope(manifest)
        if code:
            return code
        code = run_python(CAPABILITY_AUDIT, [], manifest, name="capability-audit")
        if code:
            return code
        promote_yaml_json_to_json(manifest)
        return 0
    if args.cmd == "sqlite-read-model":
        code = run_trust_envelope(manifest)
        if code:
            return code
        code = run_python(SQLITE_READ_MODEL, [], manifest, name="sqlite-read-model")
        if code:
            return code
        promote_yaml_json_to_json(manifest)
        return 0
    if args.cmd == "no-mcp-memory":
        return run_no_mcp_memory(manifest)

    code = run_python(SUITE, [args.cmd], manifest, name=f"suite:{args.cmd}")
    if code:
        return code
    promoted = promote_yaml_json_to_json(manifest)
    print(f"json-promotion {len(promoted)}")
    if args.cmd in {"semantic-layers", "graph", "all"}:
        code = run_trust_envelope(manifest)
        if code:
            return code
    if args.cmd == "all":
        for fn in [lambda: run_no_mcp_memory(manifest, ensure_envelope=False), lambda: run_graph_report(manifest), lambda: run_trust_verify(strict=args.strict, manifest=manifest), lambda: run_artifact_validation(strict=args.strict, manifest=manifest)]:
            code = fn()
            if code:
                return code
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Canonical CodeAtlas V2 runner with JSON promotion")
    parser.add_argument("cmd", choices=["doctor", "init", "snapshot", "index", "graph", "semantic-layers", "validate", "drift-check", "visualizer-export", "all", "promote-json", "trust-envelope", "verify", "graph-report", "validate-artifacts", "capability-audit", "sqlite-read-model", "no-mcp-memory"])
    parser.add_argument("--strict", action="store_true", help="Fail closed: stop at the first failed canonical step, write a run manifest, and run artifact validation in strict mode where applicable.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    manifest = RunManifest(args.cmd, args.strict, [sys.executable, str(Path(__file__)), *sys.argv[1:]])
    code = 1
    try:
        code = run_dispatch(args, manifest)
        return code
    finally:
        manifest.finish(code)


if __name__ == "__main__":
    raise SystemExit(main())
