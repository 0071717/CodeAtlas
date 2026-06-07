from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from ngk_test_helpers import EXAMPLE, ROOT, add_contract_artifacts, add_property_hub_graph

def test_review_no_agent_runs_impact_test_plan_and_context(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    add_property_hub_graph(project)
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True, text=True)
    subprocess.run(["git", "-c", "user.email=ngk@example.com", "-c", "user.name=ngk", "commit", "-m", "baseline"], cwd=project, check=True, capture_output=True, text=True)
    service = project / "api" / "app" / "services" / "property_search.py"
    service.write_text(service.read_text(encoding="utf-8") + "\n# review change\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "review",
            "--no-agent",
            "--atlas",
            str(project / ".atlas"),
            "--ngk-dir",
            str(tmp_path / ".ngk"),
            "--json",
        ],
        cwd=project,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert "api/app/services/property_search.py" in payload["changed_files"]
    assert payload["impact"]["facts"]
    assert payload["test_plan"]["plan"]["commands"]
    assert payload["drift"]["status"] == "drift"
    assert Path(payload["context_pack"]).exists()
    assert any(finding["fact_ids"] for finding in payload["findings"])
    assert payload["audit"] is None


def test_review_with_agent_audits_kiro_output(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    env = os.environ.copy()
    env["NGK_KIRO_CMD"] = (
        sys.executable
        + " -c "
        + repr('print("Review finding cites [fact.api.property_search.endpoint].")')
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "review",
            "--atlas",
            str(project / ".atlas"),
            "--ngk-dir",
            str(tmp_path / ".ngk"),
            "--json",
        ],
        cwd=project,
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    payload = json.loads(result.stdout)
    assert payload["audit"]["status"] == "passed"
    assert payload["audit"]["resolved_fact_ids"] == ["fact.api.property_search.endpoint"]


def test_contract_reports_capability_gaps_when_artifacts_missing(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    result = subprocess.run(
        [sys.executable, str(ROOT / "atlas" / "tools" / "ngk_cli.py"), "contract", "check", "--atlas", str(project / ".atlas"), "--ngk-dir", str(tmp_path / ".ngk"), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["status"] == "warn"
    assert "openapi.json artifact is missing" in payload["capability_gaps"]
    assert payload["checks"][0]["affected_facts"]
    assert payload["checks"][0]["suggested_fixes"]


def test_contract_check_passes_with_available_artifacts(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    add_contract_artifacts(project)
    result = subprocess.run(
        [sys.executable, str(ROOT / "atlas" / "tools" / "ngk_cli.py"), "contract", "check", "--atlas", str(project / ".atlas"), "--ngk-dir", str(tmp_path / ".ngk"), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert {check["check"] for check in payload["checks"]} == {"api-ui", "data"}
    assert all(check["evidence"] for check in payload["checks"])


def test_eval_init_add_and_run_without_agent(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    ngk_dir = tmp_path / ".ngk"
    init = subprocess.run(
        [sys.executable, str(ROOT / "atlas" / "tools" / "ngk_cli.py"), "eval", "init", "--atlas", str(project / ".atlas"), "--ngk-dir", str(ngk_dir)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert Path(init.stdout.strip()).exists()
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "eval",
            "add",
            "service_filters",
            "How are property search filters applied?",
            "--must-retrieve",
            "fact.data.property_search.service_filters",
            "--must-cite",
            "fact.data.property_search.service_filters",
            "--atlas",
            str(project / ".atlas"),
            "--ngk-dir",
            str(ngk_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "atlas" / "tools" / "ngk_cli.py"), "eval", "run", "--atlas", str(project / ".atlas"), "--ngk-dir", str(ngk_dir), "--json", "--strict"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["count"] >= 2
    assert all(result["audit"] is None for result in payload["results"])
