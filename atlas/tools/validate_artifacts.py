#!/usr/bin/env python3
"""Validate generated CodeAtlas artifacts without external dependencies.

This pass covers the trust-core contract for canonical facts, graph edges, and
other trust-envelope-normalized generated artefact collections in addition to
parseability, graph links, and flow step links. It intentionally implements only
the small CodeAtlas schema subset needed by generated artifacts so the validator
remains dependency-free in restricted environments.
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

ENVELOPE_COLLECTIONS = [
    ("graph/nodes", "nodes"),
    ("index/symbol-index", "symbols"),
    ("index/endpoint-index", "endpoints"),
    ("index/route-index", "routes"),
    ("index/component-index", "components"),
    ("index/hook-index", "hooks"),
    ("index/api-client-index", "api_clients"),
    ("index/schema-index", "schemas"),
    ("index/service-index", "services"),
    ("index/data-access-index", "data_access"),
    ("index/runtime-entrypoint-index", "runtime_entrypoints"),
    ("index/test-index", "tests"),
    ("index/config-index", "configs"),
    ("payloads/api-contracts", "api_contracts"),
    ("errors/error-flow-index", "error_flows"),
    ("flows/api-request-flows", "api_request_flows"),
    ("flows/ui-flows", "ui_flows"),
]

CONFIDENCE_VALUES = {"high", "medium", "low"}
STATE_VALUES = {"verified", "inferred", "unsupported", "stale", "contradicted", "partial", "unknown"}
REVIEW_STATUS_VALUES = {"unreviewed", "accepted", "rejected", "needs_clarification", "superseded"}
EDGE_TYPES = {
    "OWNS",
    "CONTAINS",
    "IMPLEMENTS",
    "CALLS",
    "MAPS_TO",
    "VALIDATES",
    "REQUIRES_PERMISSION",
    "RETURNS",
    "RAISES_ERROR",
    "DERIVED_FROM",
    "EVIDENCED_BY",
    "AFFECTS",
    "CONTRADICTS",
    "TESTS",
}
EVIDENCE_ENVELOPE_FIELDS = ["file_sha256", "commit_sha", "snippet_sha256", "extractor", "deterministic", "verification_status"]


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


def require_field(record: dict[str, Any], field: str, typ: type | tuple[type, ...], artifact: str, record_id: str, findings: list[dict[str, Any]]) -> None:
    if field not in record:
        findings.append({"severity": "error", "type": "schema_missing_required", "artifact": artifact, "record": record_id, "field": field})
        return
    if not isinstance(record[field], typ):
        findings.append({"severity": "error", "type": "schema_invalid_type", "artifact": artifact, "record": record_id, "field": field, "expected": getattr(typ, "__name__", str(typ))})


def check_provenance(record: dict[str, Any], artifact: str, record_id: str, findings: list[dict[str, Any]]) -> None:
    prov = record.get("provenance")
    if not isinstance(prov, dict):
        findings.append({"severity": "error", "type": "schema_missing_provenance", "artifact": artifact, "record": record_id})
        return
    for field in ["schema_version", "generated_at", "generator", "generator_version", "input_artifact_sha256", "source_manifest_sha256"]:
        if not prov.get(field):
            findings.append({"severity": "error", "type": "schema_invalid_provenance", "artifact": artifact, "record": record_id, "field": field})


def check_evidence(record: dict[str, Any], artifact: str, record_id: str, findings: list[dict[str, Any]]) -> None:
    evidence = record.get("evidence")
    if not isinstance(evidence, list):
        findings.append({"severity": "error", "type": "schema_invalid_evidence", "artifact": artifact, "record": record_id})
        return
    if not evidence:
        findings.append({"severity": "warning", "type": "schema_empty_evidence", "artifact": artifact, "record": record_id})
        return
    for index, ev in enumerate(evidence):
        if not isinstance(ev, dict):
            findings.append({"severity": "error", "type": "schema_invalid_evidence_item", "artifact": artifact, "record": record_id, "index": index})
            continue
        for field in EVIDENCE_ENVELOPE_FIELDS:
            if field not in ev:
                findings.append({"severity": "error", "type": "evidence_missing_envelope_field", "artifact": artifact, "record": record_id, "index": index, "field": field})
        if ev.get("type") == "code" and ev.get("repo") and ev.get("file"):
            if not ev.get("file_sha256"):
                findings.append({"severity": "error", "type": "evidence_missing_file_hash", "artifact": artifact, "record": record_id, "index": index})
            if "line_start" in ev and "line_end" in ev and not ev.get("snippet_sha256"):
                findings.append({"severity": "warning", "type": "evidence_missing_snippet_hash", "artifact": artifact, "record": record_id, "index": index})
            if ev.get("commit_sha") is None:
                findings.append({"severity": "warning", "type": "evidence_missing_commit_sha", "artifact": artifact, "record": record_id, "index": index})


def check_record_envelope(record: dict[str, Any], artifact: str, record_id: str, findings: list[dict[str, Any]]) -> None:
    require_field(record, "provenance", dict, artifact, record_id, findings)
    require_field(record, "evidence", list, artifact, record_id, findings)
    require_field(record, "state", str, artifact, record_id, findings)
    if isinstance(record.get("state"), str) and record.get("state") not in STATE_VALUES:
        findings.append({"severity": "error", "type": "schema_invalid_enum", "artifact": artifact, "record": record_id, "field": "state", "value": record.get("state")})
    check_provenance(record, artifact, record_id, findings)
    check_evidence(record, artifact, record_id, findings)


def check_additional_envelope_collections(atlas: Path, findings: list[dict[str, Any]]) -> None:
    for stem, key in ENVELOPE_COLLECTIONS:
        doc = read_first_json(atlas, stem, findings)
        if not isinstance(doc, dict) or key not in doc:
            continue
        seen: set[str] = set()
        for record in doc.get(key, []):
            if not isinstance(record, dict):
                continue
            record_id = str(record.get("id") or "<missing>")
            if record_id in seen:
                findings.append({"severity": "error", "type": "duplicate_enveloped_record_id", "artifact": f"atlas/{stem}.json", "id": record_id})
            seen.add(record_id)
            check_record_envelope(record, f"atlas/{stem}.json", record_id, findings)


def check_trust_contracts(atlas: Path, findings: list[dict[str, Any]]) -> None:
    facts_doc = read_first_json(atlas, "facts/technical-facts", findings)
    if isinstance(facts_doc, dict) and "technical_facts" in facts_doc:
        seen: set[str] = set()
        for fact in facts_doc.get("technical_facts", []):
            if not isinstance(fact, dict):
                findings.append({"severity": "error", "type": "technical_fact_not_object", "artifact": "atlas/facts/technical-facts.json"})
                continue
            record_id = str(fact.get("id") or "<missing>")
            if record_id in seen:
                findings.append({"severity": "error", "type": "duplicate_technical_fact_id", "id": record_id})
            seen.add(record_id)
            for field in ["id", "domain", "source_type", "statement", "confidence", "state"]:
                require_field(fact, field, str, "atlas/facts/technical-facts.json", record_id, findings)
            if isinstance(fact.get("confidence"), str) and fact.get("confidence") not in CONFIDENCE_VALUES:
                findings.append({"severity": "error", "type": "schema_invalid_enum", "artifact": "atlas/facts/technical-facts.json", "record": record_id, "field": "confidence", "value": fact.get("confidence")})
            if fact.get("review_status") and fact.get("review_status") not in REVIEW_STATUS_VALUES:
                findings.append({"severity": "error", "type": "schema_invalid_enum", "artifact": "atlas/facts/technical-facts.json", "record": record_id, "field": "review_status", "value": fact.get("review_status")})
            check_record_envelope(fact, "atlas/facts/technical-facts.json", record_id, findings)

    edges_doc = read_first_json(atlas, "graph/edges", findings)
    if isinstance(edges_doc, dict) and "edges" in edges_doc:
        seen_edges: set[str] = set()
        for edge in edges_doc.get("edges", []):
            if not isinstance(edge, dict):
                continue
            record_id = str(edge.get("id") or "<missing>")
            if record_id in seen_edges:
                findings.append({"severity": "error", "type": "duplicate_edge_id", "id": record_id})
            seen_edges.add(record_id)
            for field in ["id", "source", "target", "type", "confidence", "state"]:
                require_field(edge, field, str, "atlas/graph/edges.json", record_id, findings)
            if isinstance(edge.get("type"), str) and edge.get("type") not in EDGE_TYPES:
                findings.append({"severity": "error", "type": "schema_invalid_enum", "artifact": "atlas/graph/edges.json", "record": record_id, "field": "type", "value": edge.get("type")})
            if isinstance(edge.get("confidence"), str) and edge.get("confidence") not in CONFIDENCE_VALUES:
                findings.append({"severity": "error", "type": "schema_invalid_enum", "artifact": "atlas/graph/edges.json", "record": record_id, "field": "confidence", "value": edge.get("confidence")})
            check_record_envelope(edge, "atlas/graph/edges.json", record_id, findings)

    check_additional_envelope_collections(atlas, findings)


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
    check_trust_contracts(atlas, findings)
    write_report(atlas, findings, parseable_count)
    return 1 if any(f.get("severity") == "error" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
