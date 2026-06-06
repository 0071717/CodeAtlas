#!/usr/bin/env python3
"""Validate generated CodeAtlas artifacts without external dependencies.

This is a lightweight validation pass inspired by graph-first tooling practices:
parse every generated machine artifact, check graph links, check flow step links,
and emit one reviewable JSON report. It does not replace future JSON Schema
validation, but it gives Kiro/ngk an immediate deterministic gate.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
DEFAULT_ATLAS = ROOT / "atlas"

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

EXPECTED_CORE = [
    ("source/snapshot", "repositories"),
    ("index/file-index", "files"),
    ("index/symbol-index", "symbols"),
    ("graph/nodes", "nodes"),
    ("graph/edges", "edges"),
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def candidates(atlas: Path, stem: str) -> list[Path]:
    path = atlas / stem
    if path.suffix:
        if path.suffix == ".json":
            return [path, path.with_suffix(".yaml")]
        if path.suffix in {".yaml", ".yml"}:
            return [path.with_suffix(".json"), path]
        return [path]
    return [path.with_suffix(".json"), path.with_suffix(".yaml")]


def read_first_json(atlas: Path, stem: str, findings: list[dict[str, Any]]) -> Any:
    for path in candidates(atlas, stem):
        if not path.exists():
            continue
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            findings.append({"severity": "error", "type": "parse_error", "path": str(path), "message": str(exc)})
            return None
    return None


def iter_machine_artifacts(atlas: Path) -> list[Path]:
    paths: list[Path] = []
    for rel in ARTIFACT_DIRS:
        root = atlas / rel
        if not root.exists():
            continue
        paths.extend(root.rglob("*.json"))
        # Legacy V2 suite artifacts often use JSON syntax with .yaml extension.
        paths.extend(root.rglob("*.yaml"))
    return sorted({path.resolve() for path in paths})


def check_parseable(atlas: Path, findings: list[dict[str, Any]]) -> int:
    parseable = 0
    for path in iter_machine_artifacts(atlas):
        try:
            json.loads(path.read_text(encoding="utf-8"))
            parseable += 1
        except Exception as exc:
            findings.append({"severity": "error", "type": "parse_error", "path": str(path), "message": str(exc)})
    return parseable


def check_expected_core(atlas: Path, findings: list[dict[str, Any]]) -> None:
    for stem, key in EXPECTED_CORE:
        data = read_first_json(atlas, stem, findings)
        if data is None:
            findings.append({"severity": "warning", "type": "missing_core_artifact", "path": f"atlas/{stem}.json"})
            continue
        if not isinstance(data, dict) or key not in data:
            findings.append({"severity": "error", "type": "invalid_core_artifact_shape", "path": f"atlas/{stem}.json", "required_key": key})


def check_graph_links(atlas: Path, findings: list[dict[str, Any]]) -> None:
    nodes_doc = read_first_json(atlas, "graph/nodes", findings) or {}
    edges_doc = read_first_json(atlas, "graph/edges", findings) or {}
    nodes = nodes_doc.get("nodes", []) if isinstance(nodes_doc, dict) else []
    edges = edges_doc.get("edges", []) if isinstance(edges_doc, dict) else []

    node_ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict) or not node.get("id"):
            findings.append({"severity": "error", "type": "node_missing_id", "node": node})
            continue
        node_id = str(node["id"])
        if node_id in node_ids:
            findings.append({"severity": "error", "type": "duplicate_node_id", "id": node_id})
        node_ids.add(node_id)

    for edge in edges:
        if not isinstance(edge, dict):
            findings.append({"severity": "error", "type": "edge_not_object", "edge": edge})
            continue
        source = edge.get("source")
        target = edge.get("target")
        if not source or not target:
            findings.append({"severity": "error", "type": "edge_missing_endpoint", "edge": edge.get("id")})
            continue
        if str(source) not in node_ids:
            findings.append({"severity": "error", "type": "edge_broken_source", "edge": edge.get("id"), "source": source})
        if str(target) not in node_ids:
            findings.append({"severity": "error", "type": "edge_broken_target", "edge": edge.get("id"), "target": target})


def check_flow_links(atlas: Path, findings: list[dict[str, Any]]) -> None:
    nodes_doc = read_first_json(atlas, "graph/nodes", findings) or {}
    nodes = nodes_doc.get("nodes", []) if isinstance(nodes_doc, dict) else []
    node_ids = {str(node.get("id")) for node in nodes if isinstance(node, dict) and node.get("id")}
    for stem, key in [("flows/api-request-flows", "api_request_flows"), ("flows/ui-flows", "ui_flows"), ("flows/ui-action-flows", "ui_action_flows"), ("flows/error-flows", "error_flows")]:
        data = read_first_json(atlas, stem, findings)
        if not data:
            continue
        flows = data.get(key, []) if isinstance(data, dict) else []
        for flow in flows:
            if not isinstance(flow, dict):
                continue
            for step in flow.get("steps", []):
                node = step.get("node") if isinstance(step, dict) else None
                if node and str(node) not in node_ids:
                    findings.append({"severity": "warning", "type": "flow_step_unknown_node", "flow": flow.get("id"), "node": node, "artifact": f"atlas/{stem}.json"})


def write_report(atlas: Path, findings: list[dict[str, Any]], parseable_count: int) -> None:
    error_count = sum(1 for f in findings if f.get("severity") == "error")
    warning_count = sum(1 for f in findings if f.get("severity") == "warning")
    report = {
        "generated_at": now(),
        "status": "ok" if error_count == 0 else "error",
        "parseable_artifact_count": parseable_count,
        "error_count": error_count,
        "warning_count": warning_count,
        "finding_count": len(findings),
        "findings": findings,
    }
    out = atlas / "audit" / "artifact-validation-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated CodeAtlas artifacts.")
    parser.add_argument("atlas", nargs="?", default=str(DEFAULT_ATLAS), help="Path to atlas directory")
    args = parser.parse_args()

    atlas = Path(args.atlas)
    findings: list[dict[str, Any]] = []
    if not atlas.exists():
        findings.append({"severity": "error", "type": "missing_atlas_directory", "path": str(atlas)})
        write_report(atlas, findings, 0)
        return 1

    parseable_count = check_parseable(atlas, findings)
    check_expected_core(atlas, findings)
    check_graph_links(atlas, findings)
    check_flow_links(atlas, findings)
    write_report(atlas, findings, parseable_count)
    return 1 if any(f.get("severity") == "error" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
