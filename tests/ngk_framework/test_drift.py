from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from ngk_test_helpers import ATLAS, EXAMPLE, ROOT

def test_drift_reports_clean_atlas_when_metadata_is_optional(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "drift",
            "--atlas",
            str(project / ".atlas"),
            "--ngk-dir",
            str(tmp_path / ".ngk"),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    report = json.loads(result.stdout)
    assert report["status"] == "clean"
    assert report["issues"] == []


def test_drift_maps_missing_evidence_file_to_affected_fact(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    (project / "api" / "app" / "routers" / "property.py").unlink()

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "drift",
            "--atlas",
            str(project / ".atlas"),
            "--ngk-dir",
            str(tmp_path / ".ngk"),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    report = json.loads(result.stdout)
    assert report["status"] == "drift"
    assert "fact.api.property_search.endpoint" in report["affected_fact_ids"]
    assert any(issue["type"] == "missing_evidence_path" and issue["path"] == "api/app/routers/property.py" for issue in report["issues"])


def test_verify_source_spans_detects_hash_mismatch(tmp_path: Path) -> None:
    from ngk_framework.cli import file_hash_candidates

    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    source_path = project / "api" / "app" / "routers" / "property.py"
    expected_hash = sorted(file_hash_candidates(source_path, 8, 14))[0]
    spans_path = project / ".atlas" / "indexes" / "source_spans.jsonl"
    rows = [json.loads(line) for line in spans_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["content_hash"] = expected_hash
    spans_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    lines = source_path.read_text(encoding="utf-8").splitlines()
    lines[9] = lines[9] + "  # drift"
    source_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "verify-source-spans",
            "--atlas",
            str(project / ".atlas"),
            "--ngk-dir",
            str(tmp_path / ".ngk"),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    report = json.loads(result.stdout)
    assert report["status"] == "drift"
    mismatch = next(issue for issue in report["issues"] if issue["type"] == "source_span_hash_mismatch")
    assert mismatch["span_id"] == "span.api.property_router.search_endpoint"
    assert mismatch["affected_fact_ids"] == ["fact.api.property_search.endpoint"]


def test_drift_strict_mode_exits_nonzero(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    (project / "api" / "app" / "routers" / "property.py").unlink()

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "drift",
            "--atlas",
            str(project / ".atlas"),
            "--ngk-dir",
            str(tmp_path / ".ngk"),
            "--strict",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 7
    assert "WARNING missing_evidence_path" in result.stdout


def test_verify_source_spans_flags_invalid_hash_instead_of_skipping(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    spans_path = project / ".atlas" / "indexes" / "source_spans.jsonl"
    rows = [json.loads(line) for line in spans_path.read_text(encoding="utf-8").splitlines()]
    rows[0]["content_hash"] = "sha256:not-a-real-hash"
    spans_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "verify-source-spans",
            "--atlas",
            str(project / ".atlas"),
            "--ngk-dir",
            str(tmp_path / ".ngk"),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    report = json.loads(result.stdout)
    assert report["status"] == "drift"
    assert any(issue["type"] == "invalid_source_span_hash" for issue in report["issues"])
