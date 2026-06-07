from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_PATH = ROOT / "atlas" / "tools" / "codeatlas_v2_canonical.py"


def load_canonical_module():
    spec = importlib.util.spec_from_file_location("codeatlas_v2_canonical_manifest_test", CANONICAL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_run_manifest_uses_required_path_schema_and_fields(tmp_path: Path, monkeypatch) -> None:
    canonical = load_canonical_module()
    atlas = tmp_path / "atlas"
    (atlas / "audit").mkdir(parents=True)

    monkeypatch.setattr(canonical, "ATLAS", atlas)
    monkeypatch.setattr(canonical, "RUN_MANIFEST", atlas / "audit" / "run-manifest.json")
    monkeypatch.setattr(canonical, "LEGACY_RUN_MANIFEST", atlas / "audit" / "canonical-run-manifest.json")
    monkeypatch.setattr(canonical, "git_commit", lambda: "abc123")
    monkeypatch.setattr(canonical, "git_dirty_files", lambda: [" M README.md"])

    manifest = canonical.RunManifest(command=["python3", "atlas/tools/codeatlas_v2_canonical.py", "doctor", "--strict"], strict=True)
    manifest.validation_status = "failed"
    manifest.add_error("validate-artifacts failed with exit code 1")
    manifest.finish(1)

    payload = json.loads((atlas / "audit" / "run-manifest.json").read_text(encoding="utf-8"))
    legacy_payload = json.loads((atlas / "audit" / "canonical-run-manifest.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "codeatlas.run-manifest.v1"
    assert payload["run_id"].startswith("run_")
    assert payload["command"] == ["python3", "atlas/tools/codeatlas_v2_canonical.py", "doctor", "--strict"]
    assert payload["working_directory"]
    assert payload["source_commit"] == "abc123"
    assert payload["dirty_worktree"] is True
    assert payload["dirty_files"] == [" M README.md"]
    assert payload["python_version"]
    assert payload["platform"]
    assert "python" in payload["tool_versions"]
    assert isinstance(payload["input_artifacts"], list)
    assert isinstance(payload["output_artifacts"], list)
    assert payload["validation_status"] == "failed"
    assert payload["errors"]
    assert isinstance(payload["warnings"], list)
    assert legacy_payload == payload
