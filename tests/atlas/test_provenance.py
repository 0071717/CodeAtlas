"""Phase 01 acceptance tests: evidence and provenance envelope completeness."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / "atlas" / "tools"
ENVELOPE = TOOLS / "codeatlas_trust_envelope.py"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_envelope(project: Path):
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))
    spec = importlib.util.spec_from_file_location("trust_envelope_under_test", ENVELOPE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.ROOT = project
    module.ATLAS = project / "atlas"
    impl = sys.modules.get("codeatlas_trust_envelope_impl")
    if impl is not None:
        impl.ROOT = project
        impl.ATLAS = project / "atlas"
        return impl
    return module


def write_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")


def _seed_project(project: Path, *, fact_evidence=None) -> dict:
    src = project / "src"
    src.mkdir(parents=True)
    py = src / "f.py"
    py.write_text("def handler():\n    return 1\n\n# trailing\n", encoding="utf-8")
    tsx = src / "app.tsx"
    tsx.write_text("export const App = () => <Route path='/x' />;\n", encoding="utf-8")
    py_sha = sha256_bytes(py.read_bytes())
    tsx_sha = sha256_bytes(tsx.read_bytes())

    write_json(project / "atlas" / "index" / "file-index.json", {
        "generated_at": "2026-01-01T00:00:00Z",
        "files": [
            {"id": "file.testrepo.f.py", "repo": "testrepo", "path": "f.py", "language": "python",
             "classification": "source", "line_count": 4, "size_bytes": py.stat().st_size, "sha256": py_sha},
            {"id": "file.testrepo.app.tsx", "repo": "testrepo", "path": "app.tsx", "language": "typescript-react",
             "classification": "source", "line_count": 1, "size_bytes": tsx.stat().st_size, "sha256": tsx_sha},
        ],
    })
    write_json(project / "atlas" / "source" / "snapshot.json", {
        "generated_at": "2026-01-01T00:00:00Z",
        "indexed_commit": "a" * 40,
        "dirty_worktree": False,
        "repositories": [{"id": "testrepo", "path": str(src), "git_commit": "a" * 40, "dirty_worktree": False}],
    })
    fact = {
        "id": "fact.x", "domain": "d", "source_type": "endpoint", "statement": "stmt",
        "repo": "testrepo", "file": "f.py", "line_start": 1, "line_end": 2,
        "confidence": "high", "needs_review": False,
    }
    if fact_evidence is not None:
        fact["evidence"] = fact_evidence
    write_json(project / "atlas" / "facts" / "technical-facts.json", {
        "generated_at": "2026-01-01T00:00:00Z", "technical_facts": [fact],
    })
    write_json(project / "atlas" / "index" / "react-router-index.json", {
        "generated_at": "2026-01-01T00:00:00Z",
        "routes": [{"id": "route.testrepo.x", "repo": "testrepo", "file": "app.tsx", "path": "/x",
                    "kind": "jsx_route", "line_start": 1, "line_end": 1, "confidence": "medium", "needs_review": False}],
    })
    return {"py_sha": py_sha, "tsx_sha": tsx_sha}


def _run_envelope(project: Path):
    module = load_envelope(project)
    return module.run()


def test_envelope_stamps_phase01_provenance_and_evidence(tmp_path):
    hashes = _seed_project(tmp_path)
    _run_envelope(tmp_path)
    doc = json.loads((tmp_path / "atlas" / "facts" / "technical-facts.json").read_text())
    fact = doc["technical_facts"][0]

    assert doc["artifact_envelope"]["artifact_kind"] == "facts_technical_facts"
    assert doc["artifact_envelope"]["generator"]["id"] == "codeatlas_trust_envelope.py"
    assert fact["state"] == "verified"
    assert fact["provenance"]["generator"]["id"] == "codeatlas_trust_envelope.py"
    assert fact["provenance"]["generator"]["version"].startswith("2+")
    ev = fact["evidence"][0]
    assert ev["evidence_id"].startswith("ev.")
    assert ev["evidence_kind"] == "source_span"
    assert ev["source_commit"] == "a" * 40
    assert ev["file_path"] == "f.py"
    assert ev["file_hash"] == hashes["py_sha"]
    assert ev["span"] == {"start_line": 1, "end_line": 2, "start_col": 1, "end_col": 1}
    assert len(ev["snippet_hash"]) == 64
    assert ev["extractor"]["id"] == "codeatlas.v2.endpoint"
    assert ev["extractor"]["version"].startswith("2+")
    assert ev["extractor"]["kind"] == "deterministic"
    assert ev["dirty_worktree"] is False
    assert ev["verification_status"] == "current"
    assert ev["file_sha256"] == ev["file_hash"]
    assert ev["commit_sha"] == ev["source_commit"]
    assert ev["snippet_sha256"] == ev["snippet_hash"]
    assert ev["extractor_version"] == ev["extractor"]["version"]


def test_base_artifacts_get_artifact_envelope(tmp_path):
    _seed_project(tmp_path)
    _run_envelope(tmp_path)
    snapshot = json.loads((tmp_path / "atlas" / "source" / "snapshot.json").read_text())
    file_index = json.loads((tmp_path / "atlas" / "index" / "file-index.json").read_text())
    assert snapshot["artifact_envelope"]["artifact_kind"] == "source_snapshot"
    assert file_index["artifact_envelope"]["artifact_kind"] == "file_index"


def test_react_records_get_provenance_and_capped_to_inferred(tmp_path):
    _seed_project(tmp_path)
    _run_envelope(tmp_path)
    route_doc = json.loads((tmp_path / "atlas" / "index" / "react-router-index.json").read_text())
    route = route_doc["routes"][0]
    assert route_doc["artifact_envelope"]["artifact_kind"] == "react_route"
    assert route["state"] == "inferred"
    ev = route["evidence"][0]
    assert ev["file_hash"] is not None and len(ev["file_hash"]) == 64
    assert ev["extractor"]["id"] == "codeatlas.v2.react_route"
    assert ev["extractor"]["version"].startswith("2+")
    assert ev["dirty_worktree"] is False


def test_agreement_guard_flags_conflicting_file_hash(tmp_path):
    _seed_project(tmp_path, fact_evidence=[{
        "type": "code", "repo": "testrepo", "file": "f.py", "line_start": 1, "line_end": 2,
        "file_sha256": "0" * 64,
    }])
    _run_envelope(tmp_path)
    fact = json.loads((tmp_path / "atlas" / "facts" / "technical-facts.json").read_text())["technical_facts"][0]
    ev = fact["evidence"][0]
    assert ev["verification_status"] == "contradicted"
    assert ev["file_hash"] == "0" * 64
    assert ev["file_sha256"] == "0" * 64
    assert fact["state"] == "contradicted"
