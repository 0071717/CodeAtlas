from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_PATH = ROOT / "atlas" / "tools" / "codeatlas_v2_canonical.py"
VALIDATOR_PATH = ROOT / "atlas" / "tools" / "validate_artifacts.py"


def load_canonical_module():
    spec = importlib.util.spec_from_file_location("codeatlas_v2_canonical_test", CANONICAL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_script(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_strict_all_stops_at_first_failed_suite_step_and_writes_manifest(tmp_path: Path, monkeypatch) -> None:
    canonical = load_canonical_module()
    atlas = tmp_path / "atlas"
    (atlas / "audit").mkdir(parents=True)
    suite = write_script(
        tmp_path / "suite.py",
        """
from __future__ import annotations
import sys
print(f'suite:{sys.argv[1]}')
raise SystemExit(7 if sys.argv[1] == 'graph' else 0)
""".lstrip(),
    )

    monkeypatch.setattr(canonical, "ATLAS", atlas)
    monkeypatch.setattr(canonical, "SUITE", suite)
    monkeypatch.setattr(canonical, "RUN_MANIFEST", atlas / "audit" / "canonical-run-manifest.json")

    manifest = canonical.RunManifest(command="all", strict=True)
    runner = canonical.CanonicalRunner(manifest)
    exit_code = runner.run_all_strict()
    manifest.finish(exit_code)

    assert exit_code == 7
    assert [step.name for step in manifest.steps if step.name.startswith("suite:")] == [
        "suite:init",
        "suite:snapshot",
        "suite:index",
        "suite:graph",
    ]
    assert manifest.stopped_on_failure == "suite:graph"

    payload = json.loads((atlas / "audit" / "canonical-run-manifest.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == "phase00.run_manifest.v1"
    assert payload["status"] == "error"
    assert payload["exit_code"] == 7
    assert payload["steps"][-2]["name"] == "suite:graph"
    assert payload["steps"][-2]["return_code"] == 7


def test_validate_artifacts_strict_fails_closed_on_missing_core_artifacts(tmp_path: Path) -> None:
    atlas = tmp_path / "atlas"
    atlas.mkdir()

    non_strict = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), str(atlas)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert non_strict.returncode == 0
    assert json.loads(non_strict.stdout)["warning_count"] >= 1

    strict = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), str(atlas), "--strict"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert strict.returncode == 1
    payload = json.loads(strict.stdout)
    assert payload["strict"] is True
    assert payload["strict_failure_count"] >= 1
    assert payload["status"] == "error"
