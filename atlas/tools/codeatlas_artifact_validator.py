#!/usr/bin/env python3
"""Validate generated CodeAtlas artifacts.

This is a dependency-light offline validator inspired by Graphify's
validate-before-query workflow. It does not make Graphify canonical; it checks
CodeAtlas' typed filesystem artifacts before tools or Kiro trust them.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
ATLAS = ROOT / "atlas"

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

# Missing core artifacts are warnings, not hard failures, because pre-transfer
# checks may run before a target application has been configured.
CORE_ARTIFACTS = [
    ("source/snapshot.json", "repositories"),
    ("source/file-hashes.json", "files"),
    ("index/file-index.json", "files"),
    ("index/symbol-index.json", "symbols"),
    ("graph/nodes.json", "nodes"),
    ("graph/edges.json", "edges"),
    ("flows/api-request-flows.json", "api_request_flows"),
    ("flows/ui-flows.json", "ui_flows"),
    ("audit/v2-validation-report.json", "findings"),
]

SECRET_PATTERNS = [
    ("aws_access_key_id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("assigned_secret", re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key)\b\s*[:=]\s*['\"][^'\"\n]{8,}['\"]")),
]

ALLOWED_CONFIDENCE = {"high", "medium", "low", "EXTRACTED", "INFERRED", "AMBIGUOUS", None}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def candidate_paths(path: Path) -> list[Path]:
    if path.suffix == ".json":
        return [path, path.with_suffix(".yaml")]
    if path.suffix == ".yaml":
        return [path.with_suffix(".json"), path]
    return [path]


def read_jsonish(path: Path) -> tuple[Any | None, Path | None, str | None]:
    for candidate in candidate_paths(path):
        if not candidate.exists():
            continue
        try:
            return json.loads(candidate.read_text(encoding="utf-8")), candidate, None
        except Exception as exc:  # noqa: BLE001 - report exact parse failure
            return None, candidate, str(exc)
    return None, None, "missing"


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def add(findings: list[dict[str, Any]], severity: str, typ: str, **extra: Any) -> None:
    findings.append({"severity": severity, "type": typ, **extra})


def validate_core_artifacts(findings: list[dict[str, Any]]) -> None:
    for rel, expected_key in CORE_ARTIFACTS:
        canonical = ATLAS / rel
        data, actual, error = read_jsonish(canonical)
        if data is None:
            add(findings, "warning", "missing_or_unparseable_core_artifact", path=f"atlas/{rel}", detail=error)
            continue
        if actual and actual.suffix == ".yaml":
            add(findings, "warning", "legacy_yaml_artifact_used", path=str(actual), preferred=str(canonical))
        if not isinstance(data, dict):
            add(findings, "error", "artifact_root_not_object", path=str(actual))
            continue
        if expected_key not in data:
            add(findings, "warning", "artifact_missing_expected_key", path=str(actual), expected_key=expected_key)


def validate_all_jsonish_outputs(findings: list[dict[str, Any]]) -> None:
    for rel in ARTIFACT_DIRS:
        root = ATLAS / rel
        if not root.exists():
            continue
        for path in sorted(list(root.rglob("*.json")) + list(root.rglob("*.yaml"))):
            if path.name.endswith(".schema.json"):
                continue
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                add(findings, "error", "generated_artifact_parse_error", path=str(path), detail=str(exc))


def validate_graph(findings: list[dict[str, Any]]) -> None:
    nodes_doc, _, _ = read_jsonish(ATLAS / "graph/nodes.json")
    edges_doc, _, _ = read_jsonish(ATLAS / "graph/edges.json")
    nodes = nodes_doc.get("nodes", []) if isinstance(nodes_doc, dict) else []
    edges = edges_doc.get("edges", []) if isinstance(edges_doc, dict) else []

    ids: set[str] = set()
    for node in nodes:
        node_id = node.get("id") if isinstance(node, dict) else None
        if not node_id:
            add(findings, "error", "node_missing_id", node=node)
            continue
        if node_id in ids:
            add(findings, "error", "duplicate_node_id", id=node_id)
        ids.add(node_id)

    edge_ids: set[str] = set()
    for edge in edges:
        if not isinstance(edge, dict):
            add(findings, "error", "edge_not_object", edge=edge)
            continue
        edge_id = edge.get("id")
        if edge_id:
            if edge_id in edge_ids:
                add(findings, "error", "duplicate_edge_id", id=edge_id)
            edge_ids.add(edge_id)
        source = edge.get("source")
        target = edge.get("target")
        if ids and source not in ids:
            add(findings, "error", "broken_edge_source", edge=edge_id, source=source)
        if ids and target not in ids:
            add(findings, "error", "broken_edge_target", edge=edge_id, target=target)
        if edge.get("confidence") not in ALLOWED_CONFIDENCE:
            add(findings, "warning", "unknown_confidence_value", edge=edge_id, confidence=edge.get("confidence"))


def scan_for_secrets(findings: list[dict[str, Any]]) -> None:
    for rel in ARTIFACT_DIRS:
        root = ATLAS / rel
        if not root.exists():
            continue
        for path in sorted(list(root.rglob("*.json")) + list(root.rglob("*.yaml")) + list(root.rglob("*.md"))):
            try:
                if path.stat().st_size > 2_000_000:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for name, pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    add(findings, "error", "possible_secret_in_generated_artifact", path=str(path), pattern=name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated CodeAtlas artifacts.")
    parser.add_argument("--no-secret-scan", action="store_true")
    args = parser.parse_args()

    findings: list[dict[str, Any]] = []
    validate_core_artifacts(findings)
    validate_all_jsonish_outputs(findings)
    validate_graph(findings)
    if not args.no_secret_scan:
        scan_for_secrets(findings)

    status = "error" if any(f["severity"] == "error" for f in findings) else "ok" if not findings else "warning"
    report = {
        "generated_at": now(),
        "status": status,
        "finding_count": len(findings),
        "findings": findings,
        "policy": {
            "canonical_format": "json",
            "legacy_yaml_read_compatibility": True,
            "accepted_confidence_values": sorted(value for value in ALLOWED_CONFIDENCE if value is not None),
        },
    }
    write_json(ATLAS / "audit" / "artifact-validation-report.json", report)
    print(json.dumps(report, indent=2))
    return 1 if status == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
