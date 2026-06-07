from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from ngk_test_helpers import EXAMPLE, ROOT, add_property_hub_test_artifacts

def test_test_select_includes_reasons_and_coverage_gaps(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    add_property_hub_test_artifacts(project)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "test-select",
            "SearchPage",
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
    payload = json.loads(result.stdout)
    selected = {row["test_id"]: row for row in payload["selected_tests"]}
    assert "test.property_search_flow" in selected
    assert "test.ui.SearchPage" in selected
    assert "ui/src/features/property/SearchPage.test.tsx" in selected
    assert all(row["reasons"] for row in payload["selected_tests"])
    assert set(payload["coverage_gaps"]) == {"facts", "traces"}


def test_test_select_reports_coverage_gap_for_untested_impact(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "test-select",
            "api/app/services/property_search.py",
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
    payload = json.loads(result.stdout)
    assert "fact.data.property_search.service_filters" in payload["coverage_gaps"]["facts"]
    assert "trace.property_search.ui_to_api" in payload["coverage_gaps"]["traces"]


def test_test_plan_changed_uses_git_diff_status(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    add_property_hub_test_artifacts(project)
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-c", "user.email=ngk@example.com", "-c", "user.name=ngk", "commit", "-m", "baseline"],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    service = project / "api" / "app" / "services" / "property_search.py"
    service.write_text(service.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "test-plan",
            "--changed",
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
    assert "api/app/services/property_search.py" in payload["impact"]["changed_files"]
    assert "test.property_search_flow" in {row["test_id"] for row in payload["selected_tests"]}
    assert any("directly covers fact" in reason or "linked through trace" in reason for row in payload["selected_tests"] for reason in row["reasons"])
    assert payload["plan"]["commands"]
