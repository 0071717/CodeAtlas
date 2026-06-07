"""Phase 3 acceptance tests: staleness / fail-closed verify (subsystem A).

The trust envelope's verify pass re-hashes current source against the stored
evidence hashes. A source edit must flip the affected record to `stale` and
make `verify --strict` exit non-zero; an unchanged tree must stay verified.
A previously recorded `verified` is never preserved -- it is re-earned.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ENVELOPE = REPO / "atlas" / "tools" / "codeatlas_trust_envelope.py"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")


def seed(project: Path, *, fact_state: str | None = None) -> Path:
    src = project / "src"
    src.mkdir(parents=True)
    py = src / "f.py"
    py.write_text("def handler():\n    return 1\n\n# tail\n", encoding="utf-8")
    write_json(project / "atlas" / "index" / "file-index.json", {
        "generated_at": "2026-01-01T00:00:00Z",
        "files": [{"id": "file.r.f.py", "repo": "r", "path": "f.py", "language": "python",
                   "classification": "source", "line_count": 4, "size_bytes": py.stat().st_size,
                   "sha256": sha256_hex(py.read_bytes())}],
    })
    write_json(project / "atlas" / "source" / "snapshot.json", {
        "generated_at": "2026-01-01T00:00:00Z",
        "repositories": [{"id": "r", "path": str(src), "git_commit": "a" * 40, "dirty_worktree": False}],
    })
    fact = {"id": "fact.x", "domain": "d", "source_type": "endpoint", "statement": "s",
            "repo": "r", "file": "f.py", "line_start": 1, "line_end": 2,
            "confidence": "high", "needs_review": False}
    if fact_state:
        fact["state"] = fact_state
    write_json(project / "atlas" / "facts" / "technical-facts.json", {
        "generated_at": "2026-01-01T00:00:00Z", "technical_facts": [fact]})
    return py


def run_envelope(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ENVELOPE), *args], cwd=project, capture_output=True, text=True)


def fact_state(project: Path) -> str:
    doc = json.loads((project / "atlas" / "facts" / "technical-facts.json").read_text())
    return doc["technical_facts"][0]["state"]


def test_verify_clean_when_source_unchanged(tmp_path):
    seed(tmp_path)
    assert run_envelope(tmp_path).returncode == 0  # enrich
    proc = run_envelope(tmp_path, "--mode", "verify", "--strict")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert fact_state(tmp_path) == "verified"


def test_verify_marks_stale_after_source_edit_and_strict_fails(tmp_path):
    py = seed(tmp_path)
    assert run_envelope(tmp_path).returncode == 0  # enrich at T0
    assert fact_state(tmp_path) == "verified"
    # Modify a line inside the evidence span.
    py.write_text("def handler():\n    return 999\n\n# tail\n", encoding="utf-8")
    proc = run_envelope(tmp_path, "--mode", "verify", "--strict")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert fact_state(tmp_path) == "stale"


def test_prior_verified_is_not_preserved_when_source_changes(tmp_path):
    # The seed fact is pre-stamped verified, yet must be re-earned: after a
    # source change verify must downgrade it to stale.
    py = seed(tmp_path, fact_state="verified")
    assert run_envelope(tmp_path).returncode == 0  # enrich
    py.write_text("def handler():\n    return 2\n\n# changed\n", encoding="utf-8")
    proc = run_envelope(tmp_path, "--mode", "verify", "--strict")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert fact_state(tmp_path) == "stale"


def test_missing_source_file_marks_stale(tmp_path):
    py = seed(tmp_path)
    assert run_envelope(tmp_path).returncode == 0  # enrich
    py.unlink()
    proc = run_envelope(tmp_path, "--mode", "verify", "--strict")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert fact_state(tmp_path) == "stale"
