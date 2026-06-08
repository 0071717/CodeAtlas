from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[2]
CANONICAL = REPO / "atlas" / "tools" / "codeatlas_v2_canonical.py"
TOOLS = REPO / "atlas" / "tools"


def load_module():
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))
    spec = importlib.util.spec_from_file_location("codeatlas_v2_canonical_under_test", CANONICAL)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def manifest(project: Path) -> dict:
    return json.loads((project / "atlas" / "audit" / "run-manifest.json").read_text())


def configure_project(module, monkeypatch, project: Path):
    targets = [module]
    impl = sys.modules.get("codeatlas_v2_canonical_impl")
    if impl is not None:
        targets.append(impl)
    for target in targets:
        monkeypatch.setattr(target, "ROOT", project, raising=False)
        monkeypatch.setattr(target, "ATLAS", project / "atlas", raising=False)
        monkeypatch.setattr(target, "SUITE", project / "atlas" / "tools" / "codeatlas_v2_suite.py", raising=False)
        monkeypatch.setattr(target, "DOCTOR", project / "atlas" / "tools" / "codeatlas_preflight_doctor.py", raising=False)
        monkeypatch.setattr(target, "TRUST_ENVELOPE", project / "atlas" / "tools" / "codeatlas_trust_envelope.py", raising=False)
        monkeypatch.setattr(target, "ARTIFACT_VALIDATOR", project / "atlas" / "tools" / "validate_artifacts.py", raising=False)
        monkeypatch.setattr(target, "GRAPH_REPORT", project / "atlas" / "tools" / "codeatlas_graph_report.py", raising=False)
        monkeypatch.setattr(target, "CAPABILITY_AUDIT", project / "atlas" / "tools" / "codeatlas_capability_audit.py", raising=False)
        monkeypatch.setattr(target, "SQLITE_READ_MODEL", project / "atlas" / "tools" / "codeatlas_sqlite_read_model.py", raising=False)
    return impl or module


def test_all_strict_stops_at_failed_upstream_step_and_writes_manifest(tmp_path, monkeypatch):
    module = load_module()
    target = configure_project(module, monkeypatch, tmp_path)
    calls: list[str] = []

    def fake_run_python(script, args, manifest=None, name=None):
        calls.append(name or script.stem)
        exit_code = 17 if name == "suite:all" else 0
        return manifest.record_internal_step(name or script.stem, {"script": str(script), "args": args}, exit_code=exit_code)

    monkeypatch.setattr(target, "run_python", fake_run_python)
    run_manifest = target.RunManifest("all", True, [sys.executable, str(CANONICAL), "all", "--strict"])
    code = target.run_dispatch(SimpleNamespace(cmd="all", strict=True), run_manifest)
    run_manifest.finish(code)

    assert code == 17
    assert calls == ["suite:all"]
    doc = manifest(tmp_path)
    assert doc["artifact_kind"] == "run_manifest"
    assert doc["validation"]["status"] == "error"
    assert doc["data"]["strict"] is True
    assert doc["data"]["exit_code"] == 17
    assert [s["name"] for s in doc["data"]["steps"]] == ["suite:all"]
    assert doc["data"]["steps"][0]["exit_code"] == 17


def test_doctor_strict_records_ordered_successful_steps(tmp_path, monkeypatch):
    module = load_module()
    target = configure_project(module, monkeypatch, tmp_path)

    def fake_run_python(script, args, manifest=None, name=None):
        return manifest.record_internal_step(name or script.stem, {"script": str(script), "args": args}, exit_code=0)

    monkeypatch.setattr(target, "run_python", fake_run_python)
    run_manifest = target.RunManifest("doctor", True, [sys.executable, str(CANONICAL), "doctor", "--strict"])
    code = target.run_dispatch(SimpleNamespace(cmd="doctor", strict=True), run_manifest)
    run_manifest.finish(code)

    assert code == 0
    doc = manifest(tmp_path)
    assert doc["artifact_envelope"]["artifact_kind"] == "run_manifest"
    assert doc["validation"]["status"] == "ok"
    assert doc["data"]["requested_command"] == "doctor"
    names = [s["name"] for s in doc["data"]["steps"]]
    assert names == ["doctor", "promote-json", "promote-json", "trust-envelope", "promote-json", "validate-artifacts"]
    assert all(step["status"] == "ok" for step in doc["data"]["steps"])
