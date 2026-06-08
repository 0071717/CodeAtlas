#!/usr/bin/env python3
"""Strict trust/provenance implementation for canonical CodeAtlas artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from codeatlas_artifact_contract import (
    attach_artifact_envelope,
    module_version,
    normalize_evidence_item,
    now,
    provenance_descriptor,
    sha256_bytes,
    sha256_json,
    sha256_text,
    source_descriptor,
    validation_descriptor,
)

ROOT = Path.cwd()
ATLAS = ROOT / "atlas"
GENERATOR = "codeatlas_trust_envelope.py"
GENERATOR_VERSION = module_version(Path(__file__), prefix="2")
REGEX_KINDS = {"react_route", "react_query", "react_library"}

CANONICAL_COLLECTIONS = [
    ("facts/technical-facts", "technical_facts", "technical_fact"),
    ("graph/edges", "edges", "graph_edge"),
    ("graph/nodes", "nodes", "generic_record"),
    ("index/symbol-index", "symbols", "generic_record"),
    ("index/endpoint-index", "endpoints", "generic_record"),
    ("index/route-index", "routes", "generic_record"),
    ("index/component-index", "components", "generic_record"),
    ("index/hook-index", "hooks", "generic_record"),
    ("index/api-client-index", "api_clients", "generic_record"),
    ("index/schema-index", "schemas", "generic_record"),
    ("index/service-index", "services", "generic_record"),
    ("index/data-access-index", "data_access", "generic_record"),
    ("index/runtime-entrypoint-index", "runtime_entrypoints", "generic_record"),
    ("index/test-index", "tests", "generic_record"),
    ("index/config-index", "configs", "generic_record"),
    ("payloads/api-contracts", "api_contracts", "generic_record"),
    ("errors/error-flow-index", "error_flows", "generic_record"),
    ("flows/api-request-flows", "api_request_flows", "generic_record"),
    ("flows/ui-flows", "ui_flows", "generic_record"),
    ("index/react-router-index", "routes", "react_route"),
    ("index/tanstack-query-index", "queries", "react_query"),
    ("index/material-ui-index", "mui_components", "react_library"),
    ("index/leaflet-index", "leaflet_components", "react_library"),
    ("index/regraph-index", "regraph_components", "react_library"),
]
BASE_ARTIFACTS = [
    ("source/snapshot", "repositories", "source_snapshot"),
    ("source/file-hashes", "files", "source_file_hashes"),
    ("index/file-index", "files", "file_index"),
]


def candidates(stem: str) -> list[Path]:
    path = ATLAS / stem
    return [path.with_suffix(".json"), path.with_suffix(".yaml")]


def read_first(stem: str, default: Any) -> tuple[Any, Path | None]:
    for path in candidates(stem):
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8")), path
            except Exception:
                return default, path
    return default, None


def write_both(stem: str, obj: object) -> None:
    text = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    for path in candidates(stem):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def source_indexes() -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, dict[str, Any]], str]:
    file_index, _ = read_first("index/file-index", {})
    snapshot, _ = read_first("source/snapshot", {})
    files: dict[tuple[str, str], dict[str, Any]] = {}
    for rec in file_index.get("files", []) if isinstance(file_index, dict) else []:
        if isinstance(rec, dict) and rec.get("repo") and rec.get("path"):
            files[(str(rec["repo"]), str(rec["path"]))] = rec
    repos: dict[str, dict[str, Any]] = {}
    for rec in snapshot.get("repositories", []) if isinstance(snapshot, dict) else []:
        if isinstance(rec, dict) and rec.get("id"):
            repos[str(rec["id"])] = rec
    basis = {"files": file_index.get("files", []), "repositories": snapshot.get("repositories", [])} if isinstance(file_index, dict) and isinstance(snapshot, dict) else {}
    return files, repos, sha256_json(basis)


def source_path(repo_records: dict[str, dict[str, Any]], repo: str, file: str) -> Path | None:
    rec = repo_records.get(repo)
    if not rec:
        return None
    root = Path(str(rec.get("path", "")))
    return root / file if str(root) else None


def snippet_hash(repo_records: dict[str, dict[str, Any]], evidence: dict[str, Any]) -> str | None:
    repo = evidence.get("repo")
    file = evidence.get("file_path") or evidence.get("file")
    span = evidence.get("span") if isinstance(evidence.get("span"), dict) else {}
    start = span.get("start_line", evidence.get("line_start"))
    end = span.get("end_line", evidence.get("line_end", start))
    if not repo or not file or not isinstance(start, int) or not isinstance(end, int):
        return None
    path = source_path(repo_records, str(repo), str(file))
    if not path or not path.exists() or start <= 0 or end < start:
        return None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None
    return sha256_text("\n".join(lines[start - 1 : end]))


def fallback_evidence(record: dict[str, Any]) -> list[dict[str, Any]]:
    repo = record.get("repo")
    file = record.get("file") or record.get("file_path")
    if not repo or not file:
        return []
    ev: dict[str, Any] = {"type": "code", "evidence_kind": "source_span", "repo": repo, "file": file, "file_path": file}
    for key in ["line_start", "line_end", "start_col", "end_col"]:
        if isinstance(record.get(key), int):
            ev[key] = record[key]
    symbol = record.get("name") or record.get("function") or record.get("handler")
    if symbol:
        ev["symbol"] = symbol
    return [ev]


def enrich_evidence(items: Any, files: dict[tuple[str, str], dict[str, Any]], repos: dict[str, dict[str, Any]], extractor: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    stats = {"items": 0, "with_file_hash": 0, "with_commit": 0, "with_snippet_hash": 0, "unresolved": 0, "conflicts": 0}
    out: list[dict[str, Any]] = []
    for raw in items if isinstance(items, list) else []:
        if not isinstance(raw, dict):
            stats["unresolved"] += 1
            continue
        ev = dict(raw)
        ev.setdefault("type", "code")
        ev.setdefault("evidence_kind", "source_span" if ev.get("type") == "code" else "generated_artifact")
        repo = str(ev.get("repo", "")) if ev.get("repo") else ""
        file = str(ev.get("file_path") or ev.get("file") or "")
        file_rec = files.get((repo, file))
        repo_rec = repos.get(repo)
        index_sha = file_rec.get("sha256") if file_rec else None
        provided_sha = ev.get("file_hash") or ev.get("file_sha256")
        if provided_sha and index_sha and provided_sha != index_sha:
            ev["verification_status"] = "contradicted"
            stats["conflicts"] += 1
        ev.setdefault("file_hash", provided_sha or index_sha)
        ev.setdefault("source_commit", ev.get("commit_sha") or (repo_rec.get("git_commit") if repo_rec else None))
        ev.setdefault("snippet_hash", ev.get("snippet_sha256") or snippet_hash(repos, ev))
        ev.setdefault("dirty_worktree", repo_rec.get("dirty_worktree") if repo_rec else None)
        ev = normalize_evidence_item(ev, default_extractor_id=extractor, default_extractor_version=GENERATOR_VERSION)
        if ev.get("file_hash"):
            stats["with_file_hash"] += 1
        if ev.get("source_commit"):
            stats["with_commit"] += 1
        if ev.get("snippet_hash"):
            stats["with_snippet_hash"] += 1
        if ev.get("verification_status") == "contradicted":
            pass
        elif not ev.get("file_hash") or (ev.get("span") and not ev.get("snippet_hash")):
            ev["verification_status"] = "unresolved"
            stats["unresolved"] += 1
        else:
            ev["verification_status"] = "current"
        ev = normalize_evidence_item(ev, default_extractor_id=extractor, default_extractor_version=GENERATOR_VERSION)
        stats["items"] += 1
        out.append(ev)
    return out, stats


def evidence_for_record(record: dict[str, Any], files: dict[tuple[str, str], dict[str, Any]], repos: dict[str, dict[str, Any]], extractor: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    return enrich_evidence(record.get("evidence") or fallback_evidence(record), files, repos, extractor)


def record_state(record: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    statuses = {ev.get("verification_status") for ev in evidence if isinstance(ev, dict)}
    if "contradicted" in statuses:
        return "contradicted"
    if "stale" in statuses:
        return "stale"
    if not evidence:
        return "inferred" if record.get("confidence") in {"medium", "low"} else "unknown"
    if statuses == {"current"}:
        return "verified"
    return "partial"


def combine(dst: dict[str, int], src: dict[str, int]) -> None:
    for key, value in src.items():
        dst[key] = dst.get(key, 0) + int(value)


def source_context(repos: dict[str, dict[str, Any]], manifest_hash: str) -> dict[str, Any]:
    if len(repos) == 1:
        rec = next(iter(repos.values()))
        return source_descriptor(repo=str(rec.get("id") or rec.get("path") or "unknown"), source_commit=rec.get("git_commit"), dirty_worktree=rec.get("dirty_worktree"), file_manifest_hash=manifest_hash)
    commits = sorted(str(r.get("git_commit") or "") for r in repos.values())
    return source_descriptor(repo="multi" if repos else "unknown", source_commit=sha256_text("\n".join(commits)) if commits else None, dirty_worktree=any(bool(r.get("dirty_worktree")) for r in repos.values()) if repos else None, file_manifest_hash=manifest_hash)


def provenance(stem: str, path: Path | None, manifest_hash: str, original: object) -> dict[str, Any]:
    return provenance_descriptor(generator_id=GENERATOR, generator_version=GENERATOR_VERSION, command="python atlas/tools/codeatlas_trust_envelope.py", input_artifact=str(path) if path else f"atlas/{stem}.json", input_artifact_sha256=sha256_json(original), source_manifest_sha256=manifest_hash)


def artifact_kind_for(stem: str, kind: str) -> str:
    return kind if kind not in {"generic_record", "technical_fact", "graph_edge"} else stem.replace("/", "_").replace("-", "_")


def attach_doc_envelope(doc: dict[str, Any], stem: str, kind: str, manifest_hash: str, repos: dict[str, dict[str, Any]], key: str | None = None, status: str = "ok", warnings: list[Any] | None = None) -> dict[str, Any]:
    return attach_artifact_envelope(doc, stem=stem, artifact_kind=artifact_kind_for(stem, kind), generator_id=GENERATOR, generator_version=GENERATOR_VERSION, generator_command="python atlas/tools/codeatlas_trust_envelope.py", source=source_context(repos, manifest_hash), validation=validation_descriptor(status=status, validator=GENERATOR, warnings=warnings or []), data_keys=[key] if key else None)


def mark_metadata(item: dict[str, Any]) -> None:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    metadata["trust_envelope"] = {"applied": True, "version": GENERATOR_VERSION}
    item["metadata"] = metadata


def normalize_record(rec: dict[str, Any], kind: str, prov: dict[str, Any], files: dict[tuple[str, str], dict[str, Any]], repos: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], dict[str, int]]:
    item = dict(rec)
    source_type = str(item.get("source_type") or item.get("type") or "unknown")
    if kind == "technical_fact":
        item.setdefault("domain", str(item.get("domain") or item.get("repo") or "unknown"))
        item.setdefault("source_type", source_type)
        item.setdefault("claim_type", source_type)
        item.setdefault("review_status", "unreviewed" if item.get("needs_review") else "accepted")
        extractor = f"codeatlas.v2.{source_type}"
        max_state = None
    elif kind == "graph_edge":
        extractor = f"codeatlas.v2.edge.{str(item.get('type') or 'link').lower()}"
        max_state = None
    else:
        extractor = f"codeatlas.v2.{kind}"
        max_state = "inferred" if kind in REGEX_KINDS else None
    evidence, stats = evidence_for_record(item, files, repos, extractor)
    state = record_state(item, evidence)
    if max_state == "inferred" and state == "verified":
        state = "inferred"
    item["evidence"] = evidence
    item["state"] = state
    item["provenance"] = prov
    mark_metadata(item)
    return item, stats


def envelope_base_artifacts(manifest_hash: str, repos: dict[str, dict[str, Any]], report: dict[str, Any]) -> None:
    for stem, key, kind in BASE_ARTIFACTS:
        doc, _ = read_first(stem, {})
        if not isinstance(doc, dict) or key not in doc:
            continue
        doc = attach_doc_envelope(doc, stem, kind, manifest_hash, repos, key=key)
        write_both(stem, doc)
        report["collections"].append({"artifact": f"atlas/{stem}.json", "kind": kind, "status": "artifact_enveloped", "record_count": len(doc.get(key, [])) if isinstance(doc.get(key), list) else None})


def run() -> dict[str, Any]:
    files, repos, manifest_hash = source_indexes()
    report = {"generated_at": now(), "status": "ok", "generator": {"id": GENERATOR, "version": GENERATOR_VERSION, "command": "python atlas/tools/codeatlas_trust_envelope.py"}, "generator_version": GENERATOR_VERSION, "collections": [], "evidence_summary": {"items": 0, "with_file_hash": 0, "with_commit": 0, "with_snippet_hash": 0, "unresolved": 0, "conflicts": 0}}
    envelope_base_artifacts(manifest_hash, repos, report)
    for stem, key, kind in CANONICAL_COLLECTIONS:
        doc, path = read_first(stem, {})
        if not isinstance(doc, dict) or key not in doc:
            report["collections"].append({"artifact": f"atlas/{stem}.json", "kind": kind, "status": "missing"})
            continue
        original = json.loads(json.dumps(doc))
        prov = provenance(stem, path, manifest_hash, original)
        normalized: list[dict[str, Any]] = []
        local = {"items": 0, "with_file_hash": 0, "with_commit": 0, "with_snippet_hash": 0, "unresolved": 0, "conflicts": 0}
        for rec in doc.get(key, []):
            if isinstance(rec, dict):
                item, stats = normalize_record(rec, kind, prov, files, repos)
                normalized.append(item)
                combine(local, stats)
                combine(report["evidence_summary"], stats)
        doc[key] = normalized
        doc["trust_envelope"] = {"applied": True, "generated_at": now(), "generator": report["generator"], "generator_version": GENERATOR_VERSION, "source_manifest_sha256": manifest_hash}
        warnings = [{"type": "unresolved_evidence", "count": local["unresolved"]}] if local.get("unresolved") else []
        doc = attach_doc_envelope(doc, stem, kind, manifest_hash, repos, key=key, status="warning" if warnings else "ok", warnings=warnings)
        write_both(stem, doc)
        report["collections"].append({"artifact": f"atlas/{stem}.json", "kind": kind, "status": "normalized", "record_count": len(normalized), "evidence_summary": local})
    if report["evidence_summary"].get("unresolved") or report["evidence_summary"].get("conflicts"):
        report["status"] = "needs_review"
    report = attach_doc_envelope(report, "audit/trust-envelope-report", "trust_envelope_report", manifest_hash, repos, key="collections", status="warning" if report["status"] == "needs_review" else "ok")
    out = ATLAS / "audit" / "trust-envelope-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def current_file_sha256(repos: dict[str, dict[str, Any]], repo: str, file: str) -> str | None:
    path = source_path(repos, repo, file)
    if not path or not path.exists():
        return None
    try:
        return sha256_bytes(path.read_bytes())
    except Exception:
        return None


def refresh_evidence_item(ev: dict[str, Any]) -> None:
    normalized = normalize_evidence_item(ev, default_extractor_id="codeatlas.v2.verify", default_extractor_version=GENERATOR_VERSION)
    ev.clear()
    ev.update(normalized)


def verify_evidence_item(ev: dict[str, Any], repos: dict[str, dict[str, Any]]) -> str:
    repo = ev.get("repo")
    file = ev.get("file_path") or ev.get("file")
    if not repo or not file:
        return ev.get("verification_status") or "current"
    path = source_path(repos, str(repo), str(file))
    stored_file = ev.get("file_hash") or ev.get("file_sha256")
    current_file = current_file_sha256(repos, str(repo), str(file))
    stored_snip = ev.get("snippet_hash") or ev.get("snippet_sha256")
    current_snip = snippet_hash(repos, ev)
    if (path is not None and not path.exists()) or (stored_file and current_file and stored_file != current_file) or (stored_snip and current_snip and stored_snip != current_snip):
        ev["verification_status"] = "stale"
        refresh_evidence_item(ev)
        return "stale"
    if not stored_file:
        ev["verification_status"] = "unresolved"
        refresh_evidence_item(ev)
        return "unresolved"
    ev["verification_status"] = "current"
    refresh_evidence_item(ev)
    return "current"


def detect_contradictions(repos: dict[str, dict[str, Any]], manifest_hash: str) -> int:
    count = 0
    for stem, key, subject_fields in [("index/endpoint-index", "endpoints", ("method", "path")), ("index/route-index", "routes", ("path",))]:
        doc, _ = read_first(stem, {})
        if not isinstance(doc, dict) or key not in doc:
            continue
        groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
        for rec in doc.get(key, []):
            if isinstance(rec, dict):
                subject = tuple(str(rec.get(f) or "").upper() if f == "method" else str(rec.get(f) or "") for f in subject_fields)
                if all(subject):
                    groups.setdefault(subject, []).append(rec)
        changed = False
        for recs in groups.values():
            handlers = {str(r.get("handler") or r.get("function") or r.get("name") or "") for r in recs}
            handlers.discard("")
            if len(recs) > 1 and len(handlers) > 1:
                ids = [str(r.get("id")) for r in recs]
                for rec in recs:
                    rec["state"] = "contradicted"
                    rec["contradicts"] = [i for i in ids if i != str(rec.get("id"))]
                    count += 1
                    changed = True
        if changed:
            doc = attach_doc_envelope(doc, stem, key, manifest_hash, repos, key=key, status="error", warnings=[{"type": "contradicted_records", "count": count}])
            write_both(stem, doc)
    return count


def verify_run() -> dict[str, Any]:
    _, repos, manifest_hash = source_indexes()
    summary = {"records": 0, "verified": 0, "stale": 0, "contradicted": 0, "partial": 0, "inferred": 0, "unknown": 0}
    collections: list[dict[str, Any]] = []
    for stem, key, kind in CANONICAL_COLLECTIONS:
        doc, _ = read_first(stem, {})
        if not isinstance(doc, dict) or key not in doc:
            continue
        local = {"artifact": f"atlas/{stem}.json", "records": 0, "stale": 0}
        for rec in doc.get(key, []):
            if not isinstance(rec, dict):
                continue
            evidence = rec.get("evidence") if isinstance(rec.get("evidence"), list) else []
            for ev in evidence:
                if isinstance(ev, dict):
                    verify_evidence_item(ev, repos)
            rec["state"] = record_state(rec, evidence)
            summary["records"] += 1
            local["records"] += 1
            summary[rec["state"]] = summary.get(rec["state"], 0) + 1
            if rec["state"] == "stale":
                local["stale"] += 1
        doc = attach_doc_envelope(doc, stem, kind, manifest_hash, repos, key=key, status="error" if local["stale"] else "ok")
        write_both(stem, doc)
        collections.append(local)
    contradictions = detect_contradictions(repos, manifest_hash)
    summary["contradicted"] += contradictions
    status = "drift" if (summary["stale"] or summary["contradicted"]) else "ok"
    report = {"generated_at": now(), "mode": "verify", "status": status, "generator": {"id": GENERATOR, "version": GENERATOR_VERSION, "command": "python atlas/tools/codeatlas_trust_envelope.py --mode verify"}, "generator_version": GENERATOR_VERSION, "summary": summary, "collections": collections}
    report = attach_doc_envelope(report, "audit/trust-verify-report", "trust_verify_report", manifest_hash, repos, key="collections", status="error" if status == "drift" else "ok")
    out = ATLAS / "audit" / "trust-verify-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize and verify canonical CodeAtlas artifacts with trust/provenance envelopes.")
    parser.add_argument("--mode", choices=["enrich", "verify"], default="enrich")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.mode == "verify":
        report = verify_run()
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            s = report["summary"]
            print("trust-verify", f"status={report['status']}", f"records={s['records']}", f"stale={s['stale']}", f"contradicted={s['contradicted']}")
        return 1 if args.strict and (report["summary"]["stale"] or report["summary"]["contradicted"]) else 0
    report = run()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["evidence_summary"]
        print("trust-envelope", f"status={report['status']}", f"collections={len(report['collections'])}", f"evidence={summary['items']}", f"unresolved={summary['unresolved']}")
    return 0 if report["status"] in {"ok", "needs_review"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
