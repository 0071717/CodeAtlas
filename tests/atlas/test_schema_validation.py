"""Phase 1 acceptance tests for atlas/tools/validate_artifacts.py.

These prove the validator actually enforces schemas and fails closed:

* a fully valid canonical atlas passes (strict and non-strict);
* missing required trust fields / unknown enums fail (dependency-free layer);
* an empty atlas fails closed under --strict but only warns otherwise;
* the JSON Schema layer catches violations the dependency-free layer misses;
* strict mode fails closed when the jsonschema engine is unavailable.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
VALIDATOR = REPO / "atlas" / "tools" / "validate_artifacts.py"


# --- fixture builders -------------------------------------------------------


def provenance() -> dict:
    return {
        "schema_version": "1",
        "generated_at": "2026-01-01T00:00:00Z",
        "generator": "test",
        "generator_version": "1",
        "input_artifact_sha256": "a" * 64,
        "source_manifest_sha256": "b" * 64,
    }


def code_evidence() -> dict:
    return {
        "type": "code",
        "repo": "r",
        "file": "f.py",
        "symbol": "s",
        "line_start": 1,
        "line_end": 2,
        "commit_sha": "c" * 40,
        "file_sha256": "d" * 64,
        "snippet_sha256": "e" * 64,
        "extractor": "codeatlas.v2.test",
        "deterministic": True,
        "verification_status": "current",
    }


def _write(atlas: Path, stem: str, doc: dict) -> None:
    path = atlas / f"{stem}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")


def build_valid_atlas(atlas: Path) -> None:
    """Create a minimal canonical atlas that satisfies every check."""
    gen = "2026-01-01T00:00:00Z"
    _write(atlas, "source/snapshot", {"generated_at": gen, "repositories": [{"id": "r"}]})
    _write(atlas, "index/file-index", {
        "generated_at": gen,
        "files": [{
            "id": "file.x", "repo": "r", "path": "f.py", "language": "python",
            "classification": "source", "line_count": 10, "size_bytes": 100, "sha256": "f" * 64,
        }],
    })
    _write(atlas, "index/symbol-index", {
        "generated_at": gen,
        "symbols": [{
            "id": "sym.x", "state": "verified", "confidence": "high", "needs_review": False,
            "evidence": [code_evidence()], "provenance": provenance(),
        }],
    })
    _write(atlas, "graph/nodes", {
        "generated_at": gen,
        "nodes": [{
            "id": "node.x", "type": "symbol", "repo": "r", "file": "f.py", "name": "s",
            "confidence": "high", "state": "verified", "needs_review": False,
            "evidence": [code_evidence()], "provenance": provenance(),
        }],
    })
    _write(atlas, "graph/edges", {
        "generated_at": gen,
        "edges": [{
            "id": "edge.x", "source": "node.x", "target": "node.x", "type": "CALLS",
            "confidence": "high", "state": "verified", "needs_review": False,
            "evidence": [code_evidence()], "provenance": provenance(),
        }],
    })
    _write(atlas, "facts/technical-facts", {
        "generated_at": gen,
        "technical_facts": [{
            "id": "fact.x", "domain": "d", "source_type": "endpoint", "statement": "stmt",
            "confidence": "high", "state": "verified", "needs_review": False,
            "evidence": [code_evidence()], "provenance": provenance(),
        }],
    })


def run_validator(atlas: Path, strict: bool = False) -> tuple[int, dict]:
    cmd = [sys.executable, str(VALIDATOR), str(atlas)]
    if strict:
        cmd.append("--strict")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    report = json.loads(proc.stdout)
    return proc.returncode, report


def finding_types(report: dict) -> set[str]:
    return {f.get("type") for f in report.get("findings", [])}


def has_jsonschema() -> bool:
    try:
        import jsonschema  # noqa: F401
        return True
    except Exception:
        return False


# --- tests ------------------------------------------------------------------


def test_valid_atlas_passes_non_strict(tmp_path):
    build_valid_atlas(tmp_path)
    code, report = run_validator(tmp_path, strict=False)
    assert code == 0, report
    assert report["error_count"] == 0


def test_valid_atlas_passes_strict(tmp_path):
    if not has_jsonschema():
        pytest.skip("jsonschema not installed; strict happy-path requires it")
    build_valid_atlas(tmp_path)
    code, report = run_validator(tmp_path, strict=True)
    assert code == 0, report
    assert report["error_count"] == 0
    assert report["warning_count"] == 0


def test_missing_required_trust_field_fails(tmp_path):
    build_valid_atlas(tmp_path)
    # Drop the mandatory `state` field from the only fact.
    facts = json.loads((tmp_path / "facts/technical-facts.json").read_text())
    facts["technical_facts"][0].pop("state")
    _write(tmp_path, "facts/technical-facts", facts)
    code, report = run_validator(tmp_path, strict=False)
    assert code != 0, report
    assert "schema_missing_required" in finding_types(report)


def test_unknown_enum_value_fails(tmp_path):
    build_valid_atlas(tmp_path)
    facts = json.loads((tmp_path / "facts/technical-facts.json").read_text())
    facts["technical_facts"][0]["confidence"] = "extremely-high"
    _write(tmp_path, "facts/technical-facts", facts)
    code, report = run_validator(tmp_path, strict=False)
    assert code != 0, report
    assert "schema_invalid_enum" in finding_types(report)


def test_broken_edge_reference_fails(tmp_path):
    build_valid_atlas(tmp_path)
    edges = json.loads((tmp_path / "graph/edges.json").read_text())
    edges["edges"][0]["target"] = "node.does-not-exist"
    _write(tmp_path, "graph/edges", edges)
    code, report = run_validator(tmp_path, strict=False)
    assert code != 0, report
    assert "edge_broken_target" in finding_types(report)


def test_empty_atlas_warns_non_strict_but_fails_strict(tmp_path):
    atlas = tmp_path / "atlas"
    atlas.mkdir()
    code_loose, report_loose = run_validator(atlas, strict=False)
    assert code_loose == 0, report_loose
    assert report_loose["warning_count"] > 0  # missing core artifacts

    code_strict, report_strict = run_validator(atlas, strict=True)
    assert code_strict != 0, report_strict


def test_missing_atlas_directory_fails(tmp_path):
    missing = tmp_path / "nope"
    code, report = run_validator(missing, strict=False)
    assert code != 0, report
    assert "missing_atlas_directory" in finding_types(report)


def test_jsonschema_catches_what_adhoc_misses(tmp_path):
    """verification_status enum is enforced only by the JSON Schema layer."""
    if not has_jsonschema():
        pytest.skip("jsonschema not installed")
    build_valid_atlas(tmp_path)
    facts = json.loads((tmp_path / "facts/technical-facts.json").read_text())
    facts["technical_facts"][0]["evidence"][0]["verification_status"] = "bogus-status"
    _write(tmp_path, "facts/technical-facts", facts)
    code, report = run_validator(tmp_path, strict=False)
    assert code != 0, report
    assert "schema_validation_error" in finding_types(report)


def _load_module():
    spec = importlib.util.spec_from_file_location("validate_artifacts_under_test", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_strict_fails_closed_without_schema_engine(tmp_path, monkeypatch):
    """Even with a valid tree, strict must fail closed if jsonschema is unavailable."""
    build_valid_atlas(tmp_path)
    module = _load_module()
    monkeypatch.setattr(module, "load_validator_class", lambda: None)
    findings, _ = module.run_validation(tmp_path, strict=True)
    types = {f.get("type") for f in findings}
    assert "schema_engine_unavailable" in types
    engine_finding = next(f for f in findings if f.get("type") == "schema_engine_unavailable")
    assert engine_finding["severity"] == "error"
    assert module.compute_exit(findings, strict=True) != 0


def test_non_strict_tolerates_missing_schema_engine(tmp_path, monkeypatch):
    build_valid_atlas(tmp_path)
    module = _load_module()
    monkeypatch.setattr(module, "load_validator_class", lambda: None)
    findings, _ = module.run_validation(tmp_path, strict=False)
    engine_finding = next(f for f in findings if f.get("type") == "schema_engine_unavailable")
    assert engine_finding["severity"] == "warning"
    assert module.compute_exit(findings, strict=False) == 0
