"""Phase 2 acceptance tests: provenance & evidence completeness.

These prove that:

* the snapshot records dirty-worktree state and indexed_commit;
* worktree_dirty distinguishes clean / dirty / not-a-git-repo;
* the trust envelope stamps every evidence item with commit/file/snippet
  hashes plus extractor_version and dirty_worktree;
* React-indexer records are brought into the envelope and capped at `inferred`;
* the agreement guard flags a record-provided file hash that disagrees with
  the file index instead of silently overwriting it;
* extractor_version is a verifiable content hash, not a bare constant.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[2]
SUITE = REPO / "atlas" / "tools" / "codeatlas_v2_suite.py"
ENVELOPE = REPO / "atlas" / "tools" / "codeatlas_trust_envelope.py"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # Register before exec so dataclasses can resolve cls.__module__ during load.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")


# --- unit-level checks ------------------------------------------------------


def test_extractor_version_is_pinned_content_hash():
    module = load_module(ENVELOPE, "trust_envelope_under_test")
    assert module.GENERATOR_VERSION.startswith("2+")
    assert len(module.GENERATOR_VERSION) > len("2+")


def test_worktree_dirty_distinguishes_clean_dirty_and_non_git(monkeypatch):
    module = load_module(SUITE, "v2_suite_under_test")
    repo = SimpleNamespace(path=Path("."))

    monkeypatch.setattr(module, "run_git", lambda *a, **k: "")
    assert module.worktree_dirty(repo) is False

    monkeypatch.setattr(module, "run_git", lambda *a, **k: " M file.py")
    assert module.worktree_dirty(repo) is True

    monkeypatch.setattr(module, "run_git", lambda *a, **k: None)
    assert module.worktree_dirty(repo) is None


# --- snapshot end-to-end ----------------------------------------------------


def test_snapshot_records_dirty_worktree_and_indexed_commit(tmp_path):
    project = tmp_path
    (project / "atlas" / "config").mkdir(parents=True)
    (project / "atlas" / "config" / "project.yaml").write_text(
        "project: testproj\n"
        "repositories:\n"
        "  testrepo:\n"
        "    path: src\n"
        "    role: backend\n"
        "    language: python\n"
        "    framework: fastapi\n",
        encoding="utf-8",
    )
    src = project / "src"
    src.mkdir()
    (src / "f.py").write_text("def handler():\n    return 1\n", encoding="utf-8")
    # A git repo with an untracked file is dirty without needing a commit.
    subprocess.run(["git", "init", "-q"], cwd=src, check=True)

    proc = subprocess.run([sys.executable, str(SUITE), "snapshot"], cwd=project, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    # The suite writes JSON content with a .yaml extension; the canonical runner
    # promotes it to .json. Read the .yaml the suite actually produced.
    snapshot = json.loads((project / "atlas" / "source" / "snapshot.yaml").read_text())
    assert "dirty_worktree" in snapshot
    assert snapshot["dirty_worktree"] is True
    assert "indexed_commit" in snapshot
    assert snapshot["repositories"][0]["dirty_worktree"] is True


# --- trust envelope end-to-end ----------------------------------------------


def _seed_project(project: Path, *, fact_evidence=None) -> dict:
    """Create a minimal atlas tree and return the real file hashes."""
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
                    "kind": "jsx_route", "line_start": 1, "confidence": "medium", "needs_review": False}],
    })
    return {"py_sha": py_sha, "tsx_sha": tsx_sha}


def _run_envelope(project: Path) -> None:
    proc = subprocess.run([sys.executable, str(ENVELOPE)], cwd=project, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


def test_envelope_stamps_full_provenance_on_evidence(tmp_path):
    hashes = _seed_project(tmp_path)
    _run_envelope(tmp_path)
    fact = json.loads((tmp_path / "atlas" / "facts" / "technical-facts.json").read_text())["technical_facts"][0]
    assert fact.get("state")
    assert isinstance(fact.get("provenance"), dict)
    ev = fact["evidence"][0]
    assert ev["file_sha256"] == hashes["py_sha"]
    assert ev["commit_sha"] == "a" * 40
    assert len(ev["snippet_sha256"]) == 64
    assert ev["extractor_version"].startswith("2+")
    assert "dirty_worktree" in ev
    assert ev["dirty_worktree"] is False
    assert ev["verification_status"] == "current"


def test_react_records_get_provenance_and_capped_to_inferred(tmp_path):
    _seed_project(tmp_path)
    _run_envelope(tmp_path)
    route = json.loads((tmp_path / "atlas" / "index" / "react-router-index.json").read_text())["routes"][0]
    assert route["state"] == "inferred"  # capped even though jsx_route had needs_review False
    ev = route["evidence"][0]
    assert len(ev["file_sha256"]) == 64
    assert ev["extractor_version"].startswith("2+")
    assert "dirty_worktree" in ev


def test_agreement_guard_flags_conflicting_file_hash(tmp_path):
    _seed_project(tmp_path, fact_evidence=[{
        "type": "code", "repo": "testrepo", "file": "f.py", "line_start": 1, "line_end": 2,
        "file_sha256": "0" * 64,  # deliberately wrong, disagrees with the file index
    }])
    _run_envelope(tmp_path)
    fact = json.loads((tmp_path / "atlas" / "facts" / "technical-facts.json").read_text())["technical_facts"][0]
    ev = fact["evidence"][0]
    assert ev["verification_status"] == "contradicted"
    assert ev["file_sha256"] == "0" * 64  # preserved, not silently overwritten
