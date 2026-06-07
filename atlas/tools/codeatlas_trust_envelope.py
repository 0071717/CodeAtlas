#!/usr/bin/env python3
"""Attach trust/provenance envelopes to canonical CodeAtlas artifacts.

This is a deterministic post-generation normalizer. The V2 suite still emits
seed artifacts from source indexes; this pass turns those seed records into
schema-aligned canonical records by adding:

- fact fields expected by the canonical technical-fact schema (`domain`,
  `source_type`, `state`, `claim_type`)
- per-record provenance metadata
- enriched evidence with commit/file/snippet hashes when the source is available

The tool is intentionally conservative. It does not invent new facts or edges;
it only normalizes existing records and reports unresolved evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
ATLAS = ROOT / "atlas"
GENERATOR = "codeatlas_trust_envelope.py"


def _module_version() -> str:
    """Pin the extractor version to a verifiable content hash of this module so
    provenance/extractor_version is not a bare, unfalsifiable constant."""
    try:
        digest = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
    except Exception:
        digest = "unknown"
    return f"2+{digest}"


GENERATOR_VERSION = _module_version()

# Collections produced by the regex-based React indexers. They are still
# heuristic, so their records are capped at `inferred` even when evidence resolves.
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


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_json(value: object) -> str:
    return sha256_text(json.dumps(value, sort_keys=True, separators=(",", ":")))


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
    files = {}
    for rec in file_index.get("files", []) if isinstance(file_index, dict) else []:
        if isinstance(rec, dict) and rec.get("repo") and rec.get("path"):
            files[(str(rec["repo"]), str(rec["path"]))] = rec
    repos = {}
    for rec in snapshot.get("repositories", []) if isinstance(snapshot, dict) else []:
        if isinstance(rec, dict) and rec.get("id"):
            repos[str(rec["id"])] = rec
    manifest_hash = sha256_json({"files": file_index.get("files", []), "repositories": snapshot.get("repositories", [])} if isinstance(file_index, dict) and isinstance(snapshot, dict) else {})
    return files, repos, manifest_hash


def source_path(repo_records: dict[str, dict[str, Any]], repo: str, file: str) -> Path | None:
    rec = repo_records.get(repo)
    if not rec:
        return None
    root = Path(str(rec.get("path", "")))
    if not root:
        return None
    return root / file


def snippet_hash(repo_records: dict[str, dict[str, Any]], evidence: dict[str, Any]) -> str | None:
    repo = evidence.get("repo")
    file = evidence.get("file")
    start = evidence.get("line_start")
    end = evidence.get("line_end")
    if not repo or not file or not isinstance(start, int) or not isinstance(end, int):
        return None
    path = source_path(repo_records, str(repo), str(file))
    if not path or not path.exists() or start <= 0 or end < start:
        return None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None
    snippet = "\n".join(lines[start - 1 : end])
    return sha256_text(snippet)


def fallback_evidence(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Use a record's own repo/file/line fields as source evidence when possible."""
    repo = record.get("repo")
    file = record.get("file")
    if not repo or not file:
        return []
    ev: dict[str, Any] = {"type": "code", "repo": repo, "file": file}
    for key in ["line_start", "line_end"]:
        if isinstance(record.get(key), int):
            ev[key] = record[key]
    symbol = record.get("name") or record.get("function") or record.get("handler")
    if symbol:
        ev["symbol"] = symbol
    return [ev]


def enrich_evidence(
    evidence_items: Any,
    file_records: dict[tuple[str, str], dict[str, Any]],
    repo_records: dict[str, dict[str, Any]],
    extractor: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    stats = {"items": 0, "with_file_hash": 0, "with_commit": 0, "with_snippet_hash": 0, "unresolved": 0, "conflicts": 0}
    enriched: list[dict[str, Any]] = []
    raw_items = evidence_items if isinstance(evidence_items, list) else []
    for raw in raw_items:
        if not isinstance(raw, dict):
            stats["unresolved"] += 1
            continue
        ev = dict(raw)
        ev.setdefault("type", "code")
        ev.setdefault("extractor", extractor)
        ev.setdefault("extractor_version", GENERATOR_VERSION)
        ev.setdefault("deterministic", True)
        repo = str(ev.get("repo", "")) if ev.get("repo") else ""
        file = str(ev.get("file", "")) if ev.get("file") else ""
        file_rec = file_records.get((repo, file))
        repo_rec = repo_records.get(repo)
        index_sha = file_rec.get("sha256") if file_rec else None
        # Agreement guard: do not silently overwrite an extractor-provided hash;
        # if it disagrees with the file index, surface a contradiction.
        provided_sha = ev.get("file_sha256")
        if provided_sha and index_sha and provided_sha != index_sha:
            ev["verification_status"] = "contradicted"
            stats["conflicts"] += 1
        ev.setdefault("file_sha256", index_sha)
        ev.setdefault("commit_sha", repo_rec.get("git_commit") if repo_rec else None)
        ev.setdefault("snippet_sha256", snippet_hash(repo_records, ev))
        ev.setdefault("dirty_worktree", repo_rec.get("dirty_worktree") if repo_rec else None)
        if ev.get("file_sha256"):
            stats["with_file_hash"] += 1
        if ev.get("commit_sha"):
            stats["with_commit"] += 1
        if ev.get("snippet_sha256"):
            stats["with_snippet_hash"] += 1
        if not ev.get("file_sha256") or ("line_start" in ev and "line_end" in ev and not ev.get("snippet_sha256")):
            stats["unresolved"] += 1
            ev.setdefault("verification_status", "unresolved")
        else:
            ev.setdefault("verification_status", "current")
        stats["items"] += 1
        enriched.append(ev)
    return enriched, stats


def evidence_for_record(
    record: dict[str, Any],
    file_records: dict[tuple[str, str], dict[str, Any]],
    repo_records: dict[str, dict[str, Any]],
    extractor: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    raw = record.get("evidence")
    if not raw:
        raw = fallback_evidence(record)
    return enrich_evidence(raw, file_records, repo_records, extractor=extractor)


def record_state(record: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    if record.get("state"):
        return str(record["state"])
    if not evidence:
        return "unknown"
    if any(ev.get("verification_status") == "unresolved" for ev in evidence):
        return "partial"
    if record.get("needs_review"):
        return "inferred"
    return "verified"


def provenance(stem: str, path: Path | None, source_manifest_sha256: str, input_doc: object) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "generated_at": now(),
        "generator": GENERATOR,
        "generator_version": GENERATOR_VERSION,
        "input_artifact": str(path) if path else f"atlas/{stem}.json",
        "input_artifact_sha256": sha256_json(input_doc),
        "source_manifest_sha256": source_manifest_sha256,
    }


def mark_metadata(item: dict[str, Any]) -> None:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    metadata["trust_envelope"] = {"applied": True, "version": GENERATOR_VERSION}
    item["metadata"] = metadata


def normalize_fact(
    fact: dict[str, Any],
    prov: dict[str, Any],
    file_records: dict[tuple[str, str], dict[str, Any]],
    repo_records: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, int]]:
    item = dict(fact)
    source_type = str(item.get("source_type") or item.get("type") or "unknown")
    item.setdefault("domain", str(item.get("domain") or item.get("repo") or "unknown"))
    item.setdefault("source_type", source_type)
    item.setdefault("claim_type", source_type)
    if item.get("source_id") and not item.get("derived_from"):
        item["derived_from"] = [str(item["source_id"])]
    evidence, stats = evidence_for_record(item, file_records, repo_records, extractor=f"codeatlas.v2.{source_type}")
    item["evidence"] = evidence
    item["state"] = record_state(item, evidence)
    item.setdefault("review_status", "unreviewed" if item.get("needs_review") else "accepted")
    item["provenance"] = prov
    mark_metadata(item)
    return item, stats


def normalize_edge(
    edge: dict[str, Any],
    prov: dict[str, Any],
    file_records: dict[tuple[str, str], dict[str, Any]],
    repo_records: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, int]]:
    item = dict(edge)
    edge_type = str(item.get("type") or "LINKS")
    evidence, stats = evidence_for_record(item, file_records, repo_records, extractor=f"codeatlas.v2.edge.{edge_type.lower()}")
    item["evidence"] = evidence
    item["state"] = record_state(item, evidence)
    item["provenance"] = prov
    mark_metadata(item)
    return item, stats


def normalize_generic(
    record: dict[str, Any],
    prov: dict[str, Any],
    kind: str,
    file_records: dict[tuple[str, str], dict[str, Any]],
    repo_records: dict[str, dict[str, Any]],
    max_state: str | None = None,
) -> tuple[dict[str, Any], dict[str, int]]:
    item = dict(record)
    evidence, stats = evidence_for_record(item, file_records, repo_records, extractor=f"codeatlas.v2.{kind}")
    item["evidence"] = evidence
    state = record_state(item, evidence)
    # Heuristic (e.g. regex-derived React) records can never claim `verified`.
    if max_state == "inferred" and state == "verified":
        state = "inferred"
    item["state"] = state
    item["provenance"] = prov
    if max_state == "inferred":
        item["needs_review"] = True
    if "confidence" not in item:
        item["confidence"] = "high" if item["state"] == "verified" else "medium"
    if "needs_review" not in item:
        item["needs_review"] = item["state"] != "verified"
    mark_metadata(item)
    return item, stats


def combine_stats(total: dict[str, int], stats: dict[str, int]) -> None:
    for key, value in stats.items():
        total[key] = total.get(key, 0) + value


def run() -> dict[str, Any]:
    file_records, repo_records, manifest_hash = source_indexes()
    report = {
        "generated_at": now(),
        "status": "ok",
        "generator": GENERATOR,
        "generator_version": GENERATOR_VERSION,
        "collections": [],
        "evidence_summary": {"items": 0, "with_file_hash": 0, "with_commit": 0, "with_snippet_hash": 0, "unresolved": 0},
    }

    for stem, key, kind in CANONICAL_COLLECTIONS:
        doc, path = read_first(stem, {})
        if not isinstance(doc, dict) or key not in doc:
            report["collections"].append({"artifact": f"atlas/{stem}.json", "kind": kind, "status": "missing"})
            continue
        original = json.loads(json.dumps(doc))
        prov = provenance(stem, path, manifest_hash, original)
        normalized = []
        local_stats = {"items": 0, "with_file_hash": 0, "with_commit": 0, "with_snippet_hash": 0, "unresolved": 0}
        for rec in doc.get(key, []):
            if not isinstance(rec, dict):
                continue
            if kind == "technical_fact":
                item, stats = normalize_fact(rec, prov, file_records, repo_records)
            elif kind == "graph_edge":
                item, stats = normalize_edge(rec, prov, file_records, repo_records)
            else:
                max_state = "inferred" if kind in REGEX_KINDS else None
                item, stats = normalize_generic(rec, prov, kind, file_records, repo_records, max_state=max_state)
            normalized.append(item)
            combine_stats(local_stats, stats)
            combine_stats(report["evidence_summary"], stats)
        doc[key] = normalized
        doc["trust_envelope"] = {
            "applied": True,
            "generated_at": now(),
            "generator": GENERATOR,
            "generator_version": GENERATOR_VERSION,
            "source_manifest_sha256": manifest_hash,
        }
        write_both(stem, doc)
        report["collections"].append({
            "artifact": f"atlas/{stem}.json",
            "kind": kind,
            "status": "normalized",
            "record_count": len(normalized),
            "evidence_summary": local_stats,
        })

    if report["evidence_summary"]["unresolved"]:
        report["status"] = "needs_review"

    out = ATLAS / "audit" / "trust-envelope-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize canonical CodeAtlas artifacts with trust/provenance envelopes.")
    parser.add_argument("--json", action="store_true", help="Print the full JSON report")
    args = parser.parse_args()

    report = run()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        summary = report["evidence_summary"]
        print(
            "trust-envelope",
            f"status={report['status']}",
            f"collections={len(report['collections'])}",
            f"evidence={summary['items']}",
            f"unresolved={summary['unresolved']}",
        )
    return 0 if report["status"] in {"ok", "needs_review"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
