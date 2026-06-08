#!/usr/bin/env python3
"""Validate generated CodeAtlas artifacts and fail closed in strict mode."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from codeatlas_artifact_contract import CONFIDENCE_VALUES, EVIDENCE_KINDS, STATUS_VALUES, VALIDATION_STATUS_VALUES

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "config" / "schemas"
CORE_ARTIFACTS = [
    "source/snapshot",
    "index/file-index",
    "graph/nodes",
    "graph/edges",
    "facts/technical-facts",
]
RECORD_COLLECTIONS = {
    "index/symbol-index": ("symbols", None),
    "index/endpoint-index": ("endpoints", None),
    "index/route-index": ("routes", None),
    "index/component-index": ("components", None),
    "index/hook-index": ("hooks", None),
    "index/api-client-index": ("api_clients", None),
    "index/schema-index": ("schemas", None),
    "index/service-index": ("services", None),
    "index/data-access-index": ("data_access", None),
    "index/runtime-entrypoint-index": ("runtime_entrypoints", None),
    "index/test-index": ("tests", None),
    "index/config-index": ("configs", None),
    "index/react-router-index": ("routes", None),
    "index/tanstack-query-index": ("queries", None),
    "index/material-ui-index": ("mui_components", None),
    "index/leaflet-index": ("leaflet_components", None),
    "index/regraph-index": ("regraph_components", None),
    "graph/nodes": ("nodes", "map-node.schema.json"),
    "graph/edges": ("edges", "map-edge.schema.json"),
    "facts/technical-facts": ("technical_facts", "technical-fact.schema.json"),
    "payloads/api-contracts": ("api_contracts", None),
    "errors/error-flow-index": ("error_flows", None),
    "flows/api-request-flows": ("api_request_flows", None),
    "flows/ui-flows": ("ui_flows", None),
}
BASE_ARTIFACTS = {"source/snapshot", "source/file-hashes", "index/file-index"}


def finding(severity: str, typ: str, path: str, message: str, **extra: Any) -> dict[str, Any]:
    item = {"severity": severity, "type": typ, "path": path, "message": message}
    item.update(extra)
    return item


def load_validator_class():
    try:
        from jsonschema import Draft202012Validator  # type: ignore
        return Draft202012Validator
    except Exception:
        return None


def read_json(path: Path) -> tuple[Any, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, str(exc)


def artifact_path(atlas: Path, stem: str) -> Path | None:
    for suffix in [".json", ".yaml"]:
        path = atlas / f"{stem}{suffix}"
        if path.exists():
            return path
    return None


def relative_stem(atlas: Path, path: Path) -> str:
    rel = path.relative_to(atlas).as_posix()
    return rel.rsplit(".", 1)[0]


def all_artifacts(atlas: Path) -> list[Path]:
    return sorted([p for p in atlas.rglob("*.json")] + [p for p in atlas.rglob("*.yaml")])


def require_fields(obj: dict[str, Any], fields: list[str], path: str, findings: list[dict[str, Any]], typ: str = "schema_missing_required") -> None:
    for field in fields:
        if field not in obj:
            findings.append(finding("error", typ, path, f"missing required field: {field}", field=field))


def check_artifact_envelope(doc: dict[str, Any], stem: str, strict: bool, findings: list[dict[str, Any]]) -> None:
    path = f"atlas/{stem}.json"
    envelope = doc.get("artifact_envelope")
    if not isinstance(envelope, dict):
        findings.append(finding("error" if strict else "warning", "missing_artifact_envelope", path, "missing top-level artifact_envelope"))
        return
    require_fields(envelope, ["schema_version", "artifact_id", "artifact_kind", "generated_at", "generator", "source", "validation", "data"], f"{path}:artifact_envelope", findings)
    generator = envelope.get("generator")
    if not isinstance(generator, dict):
        findings.append(finding("error", "artifact_invalid_generator", path, "artifact_envelope.generator must be an object"))
    else:
        require_fields(generator, ["id", "version", "command"], f"{path}:artifact_envelope.generator", findings)
    source = envelope.get("source")
    if not isinstance(source, dict):
        findings.append(finding("error", "artifact_invalid_source", path, "artifact_envelope.source must be an object"))
    else:
        require_fields(source, ["repo", "source_commit", "dirty_worktree", "file_manifest_hash"], f"{path}:artifact_envelope.source", findings)
    validation = envelope.get("validation")
    if not isinstance(validation, dict):
        findings.append(finding("error", "artifact_invalid_validation", path, "artifact_envelope.validation must be an object"))
    else:
        require_fields(validation, ["status", "validated_at", "validator", "errors", "warnings"], f"{path}:artifact_envelope.validation", findings)
        if validation.get("status") not in VALIDATION_STATUS_VALUES:
            findings.append(finding("error", "schema_invalid_enum", f"{path}:artifact_envelope.validation.status", "invalid validation status", value=validation.get("status")))


def check_provenance(record: dict[str, Any], path: str, findings: list[dict[str, Any]]) -> None:
    prov = record.get("provenance")
    if not isinstance(prov, dict):
        findings.append(finding("error", "schema_missing_required", path, "missing required field: provenance", field="provenance"))
        return
    require_fields(prov, ["schema_version", "generated_at", "generator", "input_artifact_sha256", "source_manifest_sha256"], f"{path}.provenance", findings)
    generator = prov.get("generator")
    if not isinstance(generator, dict):
        findings.append(finding("error", "provenance_invalid_generator", path, "provenance.generator must be an object"))
    else:
        require_fields(generator, ["id", "version", "command"], f"{path}.provenance.generator", findings)


def check_evidence(record: dict[str, Any], path: str, findings: list[dict[str, Any]]) -> None:
    evidence = record.get("evidence")
    if not isinstance(evidence, list):
        findings.append(finding("error", "schema_missing_required", path, "evidence must be a list", field="evidence"))
        return
    for index, ev in enumerate(evidence):
        ev_path = f"{path}.evidence[{index}]"
        if not isinstance(ev, dict):
            findings.append(finding("error", "evidence_invalid", ev_path, "evidence item must be an object"))
            continue
        for field in ["evidence_id", "evidence_kind", "extractor", "deterministic", "verification_status"]:
            if field not in ev:
                findings.append(finding("error", "evidence_missing_envelope_field", ev_path, f"missing evidence field: {field}", field=field))
        if ev.get("evidence_kind") is not None and ev.get("evidence_kind") not in EVIDENCE_KINDS:
            findings.append(finding("error", "schema_invalid_enum", f"{ev_path}.evidence_kind", "invalid evidence_kind", value=ev.get("evidence_kind")))
        extractor = ev.get("extractor")
        if not isinstance(extractor, dict):
            findings.append(finding("error", "evidence_invalid_extractor", ev_path, "extractor must be an object with id/version/kind"))
        else:
            for field in ["id", "version", "kind"]:
                if field not in extractor:
                    findings.append(finding("error", "evidence_invalid_extractor", f"{ev_path}.extractor", f"missing extractor field: {field}", field=field))
        if ev.get("verification_status") not in {"current", "unresolved", "stale", "contradicted"}:
            findings.append(finding("error", "schema_validation_error", f"{ev_path}.verification_status", "invalid verification_status", value=ev.get("verification_status")))
        if ev.get("evidence_kind") == "source_span" or ev.get("type") == "code":
            for field in ["source_commit", "repo", "file_path", "file_hash", "span", "snippet_hash", "commit_sha", "file_sha256", "snippet_sha256", "extractor_version"]:
                if field not in ev:
                    findings.append(finding("error", "evidence_missing_envelope_field", ev_path, f"missing source evidence field: {field}", field=field))
            span = ev.get("span")
            if not isinstance(span, dict):
                findings.append(finding("error", "evidence_invalid_span", ev_path, "source evidence span must be an object"))
            else:
                for field in ["start_line", "end_line", "start_col", "end_col"]:
                    if field not in span:
                        findings.append(finding("error", "evidence_missing_envelope_field", f"{ev_path}.span", f"missing span field: {field}", field=field))


def check_record(record: dict[str, Any], path: str, findings: list[dict[str, Any]]) -> None:
    require_fields(record, ["state", "evidence", "provenance"], path, findings)
    if "confidence" in record and record.get("confidence") not in CONFIDENCE_VALUES:
        findings.append(finding("error", "schema_invalid_enum", f"{path}.confidence", "invalid confidence", value=record.get("confidence")))
    if "state" in record and record.get("state") not in STATUS_VALUES:
        findings.append(finding("error", "schema_invalid_enum", f"{path}.state", "invalid state", value=record.get("state")))
    if "evidence" in record:
        check_evidence(record, path, findings)
    if "provenance" in record:
        check_provenance(record, path, findings)


def load_schema(name: str) -> dict[str, Any] | None:
    path = SCHEMA_DIR / name
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def schema_validate(record: dict[str, Any], stem: str, schema_name: str | None, validator_class: Any, findings: list[dict[str, Any]], path: str) -> None:
    if validator_class is None:
        return
    for name in ["record-envelope.schema.json", schema_name]:
        if not name:
            continue
        schema = load_schema(name)
        if not schema:
            continue
        try:
            errors = sorted(validator_class(schema).iter_errors(record), key=lambda e: list(e.path))
        except Exception as exc:
            findings.append(finding("error", "schema_validation_error", path, f"schema validation failed to run: {exc}"))
            continue
        for err in errors:
            loc = ".".join(str(p) for p in err.path)
            findings.append(finding("error", "schema_validation_error", f"{path}.{loc}" if loc else path, err.message, schema=schema.get("$id") or name))


def check_graph_links(atlas: Path, findings: list[dict[str, Any]]) -> None:
    nodes_path = artifact_path(atlas, "graph/nodes")
    edges_path = artifact_path(atlas, "graph/edges")
    if not nodes_path or not edges_path:
        return
    nodes, err = read_json(nodes_path)
    if err or not isinstance(nodes, dict):
        return
    edges, err = read_json(edges_path)
    if err or not isinstance(edges, dict):
        return
    ids = {n.get("id") for n in nodes.get("nodes", []) if isinstance(n, dict)}
    for index, edge in enumerate(edges.get("edges", [])):
        if not isinstance(edge, dict):
            continue
        if edge.get("source") not in ids:
            findings.append(finding("error", "edge_broken_source", f"atlas/graph/edges.json.edges[{index}]", "edge source does not exist", source=edge.get("source")))
        if edge.get("target") not in ids:
            findings.append(finding("error", "edge_broken_target", f"atlas/graph/edges.json.edges[{index}]", "edge target does not exist", target=edge.get("target")))


def check_core_artifacts(atlas: Path, strict: bool, findings: list[dict[str, Any]]) -> None:
    for stem in CORE_ARTIFACTS:
        if artifact_path(atlas, stem) is None:
            findings.append(finding("error" if strict else "warning", "missing_required_artifact", f"atlas/{stem}.json", "required canonical artifact is missing"))


def run_validation(atlas: Path, strict: bool = False) -> tuple[list[dict[str, Any]], int]:
    findings: list[dict[str, Any]] = []
    atlas = Path(atlas)
    if not atlas.exists() or not atlas.is_dir():
        return [finding("error", "missing_atlas_directory", str(atlas), "atlas directory does not exist")], 0
    validator_class = load_validator_class()
    if validator_class is None:
        findings.append(finding("error" if strict else "warning", "schema_engine_unavailable", str(atlas), "jsonschema is unavailable; strict validation cannot prove schema conformance"))
    parseable_count = 0
    parsed: dict[str, dict[str, Any]] = {}
    for path in all_artifacts(atlas):
        doc, err = read_json(path)
        if err:
            findings.append(finding("error", "artifact_parse_error", str(path), err))
            continue
        parseable_count += 1
        stem = relative_stem(atlas, path)
        if isinstance(doc, dict):
            parsed[stem] = doc
    check_core_artifacts(atlas, strict, findings)
    for stem, doc in parsed.items():
        if stem.startswith("config/schemas") or stem.startswith("schemas"):
            continue
        check_artifact_envelope(doc, stem, strict, findings)
    for stem, (key, schema_name) in RECORD_COLLECTIONS.items():
        doc = parsed.get(stem)
        if not isinstance(doc, dict) or key not in doc:
            continue
        records = doc.get(key)
        if not isinstance(records, list):
            findings.append(finding("error", "schema_invalid_type", f"atlas/{stem}.json.{key}", "record collection must be a list"))
            continue
        for index, record in enumerate(records):
            path = f"atlas/{stem}.json.{key}[{index}]"
            if not isinstance(record, dict):
                findings.append(finding("error", "schema_invalid_type", path, "record must be an object"))
                continue
            check_record(record, path, findings)
            schema_validate(record, stem, schema_name, validator_class, findings, path)
    check_graph_links(atlas, findings)
    return findings, parseable_count


def compute_exit(findings: list[dict[str, Any]], strict: bool = False) -> int:
    return 1 if any(f.get("severity") == "error" for f in findings) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate generated CodeAtlas artifacts")
    parser.add_argument("atlas", nargs="?", default="atlas")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    findings, parseable_count = run_validation(Path(args.atlas), strict=args.strict)
    code = compute_exit(findings, strict=args.strict)
    report = {
        "status": "ok" if code == 0 else "error",
        "strict": args.strict,
        "parseable_artifact_count": parseable_count,
        "error_count": sum(1 for f in findings if f.get("severity") == "error"),
        "warning_count": sum(1 for f in findings if f.get("severity") == "warning"),
        "findings": findings,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
