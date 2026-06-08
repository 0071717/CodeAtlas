"""Phase 3 acceptance tests: contradiction detection (subsystem A).

Two endpoints that claim the same (method, path) with different handlers cannot
both be authoritative, so the verify pass marks both `contradicted` (with
cross-references) and `verify --strict` exits non-zero.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ENVELOPE = REPO / "atlas" / "tools" / "codeatlas_trust_envelope.py"


def write_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")


def run_verify(project: Path, strict: bool = True) -> subprocess.CompletedProcess:
    args = [sys.executable, str(ENVELOPE), "--mode", "verify"]
    if strict:
        args.append("--strict")
    return subprocess.run(args, cwd=project, capture_output=True, text=True)


def endpoints(project: Path) -> dict:
    doc = json.loads((project / "atlas" / "index" / "endpoint-index.json").read_text())
    return {e["id"]: e for e in doc["endpoints"]}


def test_conflicting_handlers_marked_contradicted_and_strict_fails(tmp_path):
    write_json(tmp_path / "atlas" / "index" / "endpoint-index.json", {
        "generated_at": "2026-01-01T00:00:00Z",
        "endpoints": [
            {"id": "ep.a", "method": "GET", "path": "/x", "handler": "handler_a"},
            {"id": "ep.b", "method": "get", "path": "/x", "handler": "handler_b"},
        ],
    })
    proc = run_verify(tmp_path, strict=True)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    eps = endpoints(tmp_path)
    assert eps["ep.a"]["state"] == "contradicted"
    assert eps["ep.b"]["state"] == "contradicted"
    assert "ep.b" in eps["ep.a"]["contradicts"]
    assert "ep.a" in eps["ep.b"]["contradicts"]


def test_distinct_routes_are_not_contradicted(tmp_path):
    write_json(tmp_path / "atlas" / "index" / "endpoint-index.json", {
        "generated_at": "2026-01-01T00:00:00Z",
        "endpoints": [
            {"id": "ep.a", "method": "GET", "path": "/x", "handler": "handler_a"},
            {"id": "ep.b", "method": "GET", "path": "/y", "handler": "handler_b"},
        ],
    })
    proc = run_verify(tmp_path, strict=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    eps = endpoints(tmp_path)
    assert eps["ep.a"]["state"] != "contradicted"
    assert eps["ep.b"]["state"] != "contradicted"


def test_same_route_same_handler_is_not_contradicted(tmp_path):
    write_json(tmp_path / "atlas" / "index" / "endpoint-index.json", {
        "generated_at": "2026-01-01T00:00:00Z",
        "endpoints": [
            {"id": "ep.a", "method": "GET", "path": "/x", "handler": "shared"},
            {"id": "ep.b", "method": "GET", "path": "/x", "handler": "shared"},
        ],
    })
    proc = run_verify(tmp_path, strict=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
