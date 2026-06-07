from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "atlas" / "tools" / "validate_artifacts.py"
SQLITE_PATH = ROOT / "atlas" / "tools" / "codeatlas_sqlite_read_model.py"
CONTEXT_PATH = ROOT / "atlas" / "tools" / "codeatlas_context_pack.py"
CANONICAL_PATH = ROOT / "atlas" / "tools" / "codeatlas_v2_canonical.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_script(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def envelope(kind: str, data: dict) -> dict:
    return {
        "schema_version": f"codeatlas.{kind}.v1",
        "artifact_id": f"artifact.{kind}",
        "artifact_kind": kind,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "generator": {"id": "test", "version": "0", "command": ["test"]},
        "source": {"repo": "fixture", "source_commit": "abc123", "dirty_worktree": False, "file_manifest_hash": "sha256:manifest"},
        "validation": {"status": "passed", "validated_at": "2026-01-01T00:00:00+00:00", "validator": "test", "errors": [], "warnings": []},
        "data": data,
    }


def provenance() -> dict:
    return {
        "schema_version": "codeatlas.provenance.v1",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "generator": "test",
        "generator_version": "0",
        "input_artifact_sha256": "sha256:input",
        "source_manifest_sha256": "sha256:manifest",
    }


def evidence() -> list[dict]:
    return [
        {
            "evidence_kind": "source_span",
            "file_sha256": "sha256:file",
            "commit_sha": "abc123",
            "snippet_sha256": "sha256:snippet",
            "extractor": "test",
            "deterministic": True,
            "verification_status": "verified",
        }
    ]


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_minimal_core(atlas: Path, *, broken_edge: bool = False, missing_evidence: bool = False) -> None:
    write_json(atlas / "source" / "snapshot.json", envelope("source-snapshot", {"repositories": []}))
    write_json(atlas / "index" / "file-index.json", envelope("file-index", {"files": []}))
    write_json(atlas / "index" / "symbol-index.json", envelope("symbol-index", {"symbols": []}))
    node = {"id": "node.a", "state": "verified", "provenance": provenance(), "evidence": [] if missing_evidence else evidence()}
    edge = {
        "id": "edge.a",
        "source": "node.a",
        "target": "node.missing" if broken_edge else "node.a",
        "type": "CALLS",
        "confidence": "high",
        "state": "verified",
        "provenance": provenance(),
        "evidence": evidence(),
    }
    write_json(atlas / "graph" / "nodes.json", envelope("graph-nodes", {"nodes": [node]}))
    write_json(atlas / "graph" / "edges.json", envelope("graph-edges", {"edges": [edge]}))


def run_validator(atlas: Path, strict: bool = True) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(VALIDATOR_PATH), str(atlas)]
    if strict:
        args.append("--strict")
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)


def test_invalid_json_artifact_blocks_strict_run(tmp_path: Path) -> None:
    atlas = tmp_path / "atlas"
    (atlas / "graph").mkdir(parents=True)
    (atlas / "graph" / "nodes.json").write_text("{not valid json", encoding="utf-8")

    result = run_validator(atlas, strict=True)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert any(f["type"] == "parse_error" for f in payload["findings"])


def test_missing_evidence_blocks_strict_run(tmp_path: Path) -> None:
    atlas = tmp_path / "atlas"
    write_minimal_core(atlas, missing_evidence=True)

    result = run_validator(atlas, strict=True)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert any(f["type"] == "schema_empty_evidence" for f in payload["findings"])


def test_broken_graph_edge_blocks_strict_run(tmp_path: Path) -> None:
    atlas = tmp_path / "atlas"
    write_minimal_core(atlas, broken_edge=True)

    result = run_validator(atlas, strict=True)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert any(f["type"] == "edge_broken_target" for f in payload["findings"])


def test_sqlite_strict_refuses_to_write_database_after_failed_validation(tmp_path: Path, monkeypatch) -> None:
    sqlite_tool = load_module("sqlite_phase00_test", SQLITE_PATH)
    atlas = tmp_path / "atlas"
    db = atlas / "knowledge" / "atlas.sqlite"
    validator = write_script(tmp_path / "validator.py", "raise SystemExit(5)\n")

    monkeypatch.setattr(sqlite_tool, "ATLAS", atlas)
    monkeypatch.setattr(sqlite_tool, "DB", db)
    monkeypatch.setattr(sqlite_tool, "VALIDATOR", validator)
    monkeypatch.setattr(sys, "argv", ["codeatlas_sqlite_read_model.py", "--strict"])

    assert sqlite_tool.main() == 5
    assert not db.exists()


def test_context_pack_strict_refuses_to_write_after_failed_validation(tmp_path: Path, monkeypatch) -> None:
    context_tool = load_module("context_phase00_test", CONTEXT_PATH)
    atlas = tmp_path / "atlas"
    validator = write_script(tmp_path / "validator.py", "raise SystemExit(6)\n")

    monkeypatch.setattr(context_tool, "ATLAS", atlas)
    monkeypatch.setattr(context_tool, "DB", atlas / "knowledge" / "atlas.sqlite")
    monkeypatch.setattr(context_tool, "VALIDATOR", validator)
    monkeypatch.setattr(sys, "argv", ["codeatlas_context_pack.py", "build", "claims", "--strict"])

    assert context_tool.main() == 6
    assert not (atlas / "context-packs").exists()


def test_doctor_strict_exits_nonzero_when_artifact_validation_fails(tmp_path: Path, monkeypatch) -> None:
    canonical = load_module("canonical_phase00_doctor_test", CANONICAL_PATH)
    atlas = tmp_path / "atlas"
    (atlas / "audit").mkdir(parents=True)
    ok = write_script(tmp_path / "ok.py", "raise SystemExit(0)\n")
    validator = write_script(
        tmp_path / "validator.py",
        """
from __future__ import annotations
import json, sys
from pathlib import Path
atlas = Path(sys.argv[1])
(atlas / 'audit').mkdir(parents=True, exist_ok=True)
(atlas / 'audit' / 'artifact-validation-report.json').write_text(json.dumps({'status': 'error', 'findings': [{'severity': 'error', 'type': 'parse_error'}]}))
raise SystemExit(7)
""".lstrip(),
    )

    monkeypatch.setattr(canonical, "ATLAS", atlas)
    monkeypatch.setattr(canonical, "DOCTOR", ok)
    monkeypatch.setattr(canonical, "TRUST_ENVELOPE", ok)
    monkeypatch.setattr(canonical, "ARTIFACT_VALIDATOR", validator)
    monkeypatch.setattr(canonical, "RUN_MANIFEST", atlas / "audit" / "run-manifest.json")
    monkeypatch.setattr(canonical, "LEGACY_RUN_MANIFEST", atlas / "audit" / "canonical-run-manifest.json")
    monkeypatch.setattr(sys, "argv", ["codeatlas_v2_canonical.py", "doctor", "--strict"])

    assert canonical.main() == 7
    payload = json.loads((atlas / "audit" / "run-manifest.json").read_text(encoding="utf-8"))
    assert payload["validation_status"] == "failed"
