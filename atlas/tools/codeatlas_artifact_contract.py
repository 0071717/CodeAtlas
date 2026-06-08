#!/usr/bin/env python3
"""Shared CodeAtlas evidence, provenance, and artifact-envelope helpers.

The helpers in this module are dependency-free on purpose. Canonical tools can
use them before JSON Schema validation is available, and validators can use the
same vocabulary without importing generator-specific code.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1"

STATUS_VALUES = {"verified", "inferred", "unsupported", "stale", "contradicted", "partial", "unknown"}
CONFIDENCE_VALUES = {"high", "medium", "low", "none"}
EVIDENCE_KINDS = {
    "source_span",
    "openapi_operation",
    "test_definition",
    "test_result",
    "runtime_trace",
    "git_history",
    "config_value",
    "generated_artifact",
    "human_review",
    "llm_finding",
    "external_finding",
}
VALIDATION_STATUS_VALUES = {"ok", "warning", "error", "needs_review", "unknown"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(value: object) -> str:
    return sha256_text(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str))


def stable_slug(value: object) -> str:
    text = str(value).replace("\\", "/").strip("/")
    text = re.sub(r"[^A-Za-z0-9_./:-]+", "_", text)
    text = text.replace("/", ".").replace("-", "_").replace(":", ".")
    return re.sub(r"\.+", ".", text).strip(".") or "root"


def module_version(path: Path, prefix: str = "1") -> str:
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    except Exception:
        digest = "unknown"
    return f"{prefix}+{digest}"


def git_value(root: Path, *args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), *args],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return None


def git_dirty(root: Path) -> bool | None:
    status = git_value(root, "status", "--porcelain")
    if status is None:
        return None
    return bool(status.strip())


def command_string(argv: list[str] | tuple[str, ...] | None = None) -> str:
    parts = list(argv) if argv is not None else sys.argv
    return " ".join(str(part) for part in parts)


def generator(id: str, version: str, command: str | None = None) -> dict[str, str]:
    return {"id": id, "version": version, "command": command or command_string()}


def source_descriptor(
    *,
    repo: str | None = None,
    source_commit: str | None = None,
    dirty_worktree: bool | None = None,
    file_manifest_hash: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Build the source block used by artifact envelopes.

    `repo` is a stable descriptor of the source being indexed. In local runs it
    is commonly the working directory; when a source snapshot exists, callers can
    supply the logical repo id/path instead.
    """
    if root is not None:
        source_commit = source_commit if source_commit is not None else git_value(root, "rev-parse", "HEAD")
        dirty_worktree = dirty_worktree if dirty_worktree is not None else git_dirty(root)
        repo = repo if repo is not None else str(root)
    return {
        "repo": repo or "unknown",
        "source_commit": source_commit,
        "dirty_worktree": dirty_worktree,
        "file_manifest_hash": file_manifest_hash,
    }


def validation_descriptor(
    *,
    status: str = "unknown",
    validator: str,
    errors: list[Any] | None = None,
    warnings: list[Any] | None = None,
    validated_at: str | None = None,
) -> dict[str, Any]:
    if status not in VALIDATION_STATUS_VALUES:
        status = "unknown"
    return {
        "status": status,
        "validated_at": validated_at or now(),
        "validator": validator,
        "errors": errors or [],
        "warnings": warnings or [],
    }


def _extractor_object(raw: Any, *, default_id: str, default_version: str, default_kind: str) -> dict[str, str]:
    if isinstance(raw, dict):
        extractor_id = str(raw.get("id") or default_id)
        version = str(raw.get("version") or default_version)
        kind = str(raw.get("kind") or default_kind)
        command = raw.get("command")
    else:
        extractor_id = str(raw or default_id)
        version = default_version
        kind = default_kind
        command = None
    result = {"id": extractor_id, "version": version, "kind": kind}
    if command:
        result["command"] = str(command)
    return result


def normalize_evidence_item(
    evidence: dict[str, Any],
    *,
    default_extractor_id: str,
    default_extractor_version: str,
    default_extractor_kind: str = "deterministic",
) -> dict[str, Any]:
    """Return an evidence item carrying both canonical and legacy aliases.

    Canonical source-backed fields follow the Phase 01 contract
    (`evidence_id`, `evidence_kind`, `source_commit`, `file_path`, `file_hash`,
    `span`, `snippet_hash`, `extractor.{id,version,kind}`). Legacy aliases are
    kept (`commit_sha`, `file_sha256`, `snippet_sha256`, etc.) so older readers
    remain deterministic while they migrate.
    """
    ev = dict(evidence)
    ev.setdefault("type", "code")
    ev.setdefault("evidence_kind", "source_span" if ev.get("type") == "code" else "generated_artifact")

    source_commit = ev.get("source_commit", ev.get("commit_sha"))
    file_path = ev.get("file_path", ev.get("file"))
    file_hash = ev.get("file_hash", ev.get("file_sha256"))
    snippet_hash = ev.get("snippet_hash", ev.get("snippet_sha256"))

    span = ev.get("span") if isinstance(ev.get("span"), dict) else {}
    start_line = span.get("start_line", ev.get("line_start"))
    end_line = span.get("end_line", ev.get("line_end", start_line))
    start_col = span.get("start_col", ev.get("start_col", 1 if start_line else None))
    end_col = span.get("end_col", ev.get("end_col", start_col))
    if start_line is not None or end_line is not None or start_col is not None or end_col is not None:
        ev["span"] = {
            "start_line": start_line,
            "end_line": end_line,
            "start_col": start_col,
            "end_col": end_col,
        }

    extractor_version = str(ev.get("extractor_version") or default_extractor_version)
    extractor = _extractor_object(
        ev.get("extractor"),
        default_id=default_extractor_id,
        default_version=extractor_version,
        default_kind=default_extractor_kind,
    )

    ev["extractor"] = extractor
    ev.setdefault("extractor_id", extractor["id"])
    ev["extractor_version"] = extractor["version"]
    ev.setdefault("extractor_kind", extractor["kind"])

    ev["source_commit"] = source_commit
    ev["file_path"] = file_path
    ev["file_hash"] = file_hash
    ev["snippet_hash"] = snippet_hash

    # Legacy aliases remain first-class until all downstream tools migrate.
    ev["commit_sha"] = source_commit
    ev["file"] = file_path
    ev["file_sha256"] = file_hash
    ev["snippet_sha256"] = snippet_hash
    if isinstance(ev.get("span"), dict):
        ev["line_start"] = ev["span"].get("start_line")
        ev["line_end"] = ev["span"].get("end_line")
        ev["start_col"] = ev["span"].get("start_col")
        ev["end_col"] = ev["span"].get("end_col")

    ev.setdefault("deterministic", True)
    ev.setdefault("verification_status", "unresolved")
    ev["evidence_id"] = ev.get("evidence_id") or f"ev.{sha256_json({k: ev.get(k) for k in ['evidence_kind', 'repo', 'file_path', 'span', 'source_commit', 'file_hash', 'snippet_hash', 'extractor_id']})[:24]}"
    return ev


def provenance_descriptor(
    *,
    generator_id: str,
    generator_version: str,
    input_artifact_sha256: str,
    source_manifest_sha256: str,
    input_artifact: str | None = None,
    command: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    gen = generator(generator_id, generator_version, command)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at or now(),
        "generator": gen,
        # Legacy aliases are kept for older schema-aware tools.
        "generator_id": gen["id"],
        "generator_version": gen["version"],
        "generator_command": gen["command"],
        "input_artifact": input_artifact,
        "input_artifact_sha256": input_artifact_sha256,
        "source_manifest_sha256": source_manifest_sha256,
    }


def artifact_envelope(
    *,
    artifact_id: str,
    artifact_kind: str,
    generator_id: str,
    generator_version: str,
    generator_command: str,
    source: dict[str, Any],
    validation: dict[str, Any],
    data: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": artifact_id,
        "artifact_kind": artifact_kind,
        "generated_at": generated_at or now(),
        "generator": generator(generator_id, generator_version, generator_command),
        "source": source,
        "validation": validation,
        "data": data or {},
    }


def attach_artifact_envelope(
    doc: dict[str, Any],
    *,
    stem: str,
    artifact_kind: str,
    generator_id: str,
    generator_version: str,
    generator_command: str | None,
    source: dict[str, Any],
    validation: dict[str, Any] | None = None,
    data_keys: list[str] | None = None,
) -> dict[str, Any]:
    """Attach a non-breaking top-level artifact envelope to a canonical doc."""
    result = dict(doc)
    payload = {k: v for k, v in result.items() if k != "artifact_envelope"}
    if data_keys is None:
        data_keys = sorted(k for k in payload if k not in {"generated_at", "trust_envelope"})
    result["artifact_envelope"] = artifact_envelope(
        artifact_id=f"codeatlas.{stable_slug(stem)}",
        artifact_kind=artifact_kind,
        generator_id=generator_id,
        generator_version=generator_version,
        generator_command=generator_command or command_string(),
        source=source,
        validation=validation or validation_descriptor(status="unknown", validator=generator_id),
        data={
            "payload_hash": sha256_json(payload),
            "root_keys": sorted(payload.keys()),
            "data_keys": data_keys,
        },
    )
    return result
