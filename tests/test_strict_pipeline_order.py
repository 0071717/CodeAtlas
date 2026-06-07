from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_PATH = ROOT / "atlas" / "tools" / "codeatlas_v2_canonical.py"


def load_canonical_module():
    spec = importlib.util.spec_from_file_location("codeatlas_v2_canonical_order_test", CANONICAL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_script(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_all_strict_validates_before_sqlite_context_and_graph_report(tmp_path: Path, monkeypatch) -> None:
    canonical = load_canonical_module()
    atlas = tmp_path / "atlas"
    (atlas / "audit").mkdir(parents=True)
    log = tmp_path / "order.log"

    suite = write_script(
        tmp_path / "suite.py",
        f"""
from __future__ import annotations
import sys
from pathlib import Path
Path({str(log)!r}).write_text(Path({str(log)!r}).read_text() + 'suite:' + sys.argv[1] + '\\n' if Path({str(log)!r}).exists() else 'suite:' + sys.argv[1] + '\\n')
raise SystemExit(0)
""".lstrip(),
    )
    validator = write_script(
        tmp_path / "validator.py",
        f"""
from __future__ import annotations
import json, sys
from pathlib import Path
log = Path({str(log)!r})
log.write_text((log.read_text() if log.exists() else '') + 'validator\\n')
atlas = Path(sys.argv[1])
(atlas / 'audit').mkdir(parents=True, exist_ok=True)
(atlas / 'audit' / 'artifact-validation-report.json').write_text(json.dumps({{'status': 'ok', 'findings': []}}))
raise SystemExit(0)
""".lstrip(),
    )
    marker_scripts = {}
    for name in ["trust", "capability", "sqlite", "context", "graph_report"]:
        marker_scripts[name] = write_script(
            tmp_path / f"{name}.py",
            f"""
from __future__ import annotations
from pathlib import Path
log = Path({str(log)!r})
log.write_text((log.read_text() if log.exists() else '') + {name!r} + '\\n')
raise SystemExit(0)
""".lstrip(),
        )

    monkeypatch.setattr(canonical, "ATLAS", atlas)
    monkeypatch.setattr(canonical, "SUITE", suite)
    monkeypatch.setattr(canonical, "ARTIFACT_VALIDATOR", validator)
    monkeypatch.setattr(canonical, "TRUST_ENVELOPE", marker_scripts["trust"])
    monkeypatch.setattr(canonical, "CAPABILITY_AUDIT", marker_scripts["capability"])
    monkeypatch.setattr(canonical, "SQLITE_READ_MODEL", marker_scripts["sqlite"])
    monkeypatch.setattr(canonical, "CONTEXT_PACK", marker_scripts["context"])
    monkeypatch.setattr(canonical, "GRAPH_REPORT", marker_scripts["graph_report"])
    monkeypatch.setattr(canonical, "RUN_MANIFEST", atlas / "audit" / "run-manifest.json")
    monkeypatch.setattr(canonical, "LEGACY_RUN_MANIFEST", atlas / "audit" / "canonical-run-manifest.json")

    manifest = canonical.RunManifest(command=["all", "--strict"], strict=True)
    runner = canonical.CanonicalRunner(manifest)
    exit_code = runner.run_all_strict()
    manifest.finish(exit_code)

    assert exit_code == 0
    events = log.read_text(encoding="utf-8").splitlines()
    assert "validator" in events
    assert "sqlite" in events
    assert "context" in events
    assert "graph_report" in events
    assert events.index("validator") < events.index("sqlite")
    assert events.index("validator") < events.index("context")
    assert events.index("validator") < events.index("graph_report")


def test_all_strict_stops_before_sqlite_when_validation_fails(tmp_path: Path, monkeypatch) -> None:
    canonical = load_canonical_module()
    atlas = tmp_path / "atlas"
    (atlas / "audit").mkdir(parents=True)
    log = tmp_path / "order.log"

    suite = write_script(
        tmp_path / "suite.py",
        f"""
from __future__ import annotations
import sys
from pathlib import Path
log = Path({str(log)!r})
log.write_text((log.read_text() if log.exists() else '') + 'suite:' + sys.argv[1] + '\\n')
raise SystemExit(0)
""".lstrip(),
    )
    validator = write_script(
        tmp_path / "validator.py",
        f"""
from __future__ import annotations
import json, sys
from pathlib import Path
log = Path({str(log)!r})
log.write_text((log.read_text() if log.exists() else '') + 'validator\\n')
atlas = Path(sys.argv[1])
(atlas / 'audit').mkdir(parents=True, exist_ok=True)
(atlas / 'audit' / 'artifact-validation-report.json').write_text(json.dumps({{'status': 'error', 'findings': [{{'severity': 'error', 'type': 'missing_artifact_envelope'}}]}}))
raise SystemExit(9)
""".lstrip(),
    )
    ok_script = write_script(
        tmp_path / "ok.py",
        "raise SystemExit(0)\n",
    )
    sqlite = write_script(
        tmp_path / "sqlite.py",
        f"""
from pathlib import Path
Path({str(log)!r}).write_text(Path({str(log)!r}).read_text() + 'sqlite\\n')
raise SystemExit(0)
""".lstrip(),
    )

    monkeypatch.setattr(canonical, "ATLAS", atlas)
    monkeypatch.setattr(canonical, "SUITE", suite)
    monkeypatch.setattr(canonical, "ARTIFACT_VALIDATOR", validator)
    monkeypatch.setattr(canonical, "TRUST_ENVELOPE", ok_script)
    monkeypatch.setattr(canonical, "CAPABILITY_AUDIT", ok_script)
    monkeypatch.setattr(canonical, "SQLITE_READ_MODEL", sqlite)
    monkeypatch.setattr(canonical, "CONTEXT_PACK", ok_script)
    monkeypatch.setattr(canonical, "GRAPH_REPORT", ok_script)
    monkeypatch.setattr(canonical, "RUN_MANIFEST", atlas / "audit" / "run-manifest.json")
    monkeypatch.setattr(canonical, "LEGACY_RUN_MANIFEST", atlas / "audit" / "canonical-run-manifest.json")

    manifest = canonical.RunManifest(command=["all", "--strict"], strict=True)
    runner = canonical.CanonicalRunner(manifest)
    exit_code = runner.run_all_strict()
    manifest.finish(exit_code)

    assert exit_code == 9
    events = log.read_text(encoding="utf-8").splitlines()
    assert "validator" in events
    assert "sqlite" not in events
    assert manifest.stopped_on_failure == "validate-artifacts"
