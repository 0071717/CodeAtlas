from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from ngk_test_helpers import EXAMPLE, ROOT, add_property_hub_graph

def test_graph_neighbors_and_reverse_neighbors(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    add_property_hub_graph(project)
    base = ["--atlas", str(project / ".atlas"), "--ngk-dir", str(tmp_path / ".ngk")]

    forward = subprocess.run(
        [sys.executable, str(ROOT / "atlas" / "tools" / "ngk_cli.py"), "graph", "neighbors", "SearchPage", *base, "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(forward.stdout)
    assert payload["matched_target"]["node_id"] == "span.ui.property_search_page"
    assert payload["neighbors"][0]["node_id"] == "span.ui.use_property_search_query"

    reverse = subprocess.run(
        [sys.executable, str(ROOT / "atlas" / "tools" / "ngk_cli.py"), "graph", "neighbors", "span.api.property_router.search_endpoint", *base, "--reverse", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(reverse.stdout)
    assert payload["direction"] == "reverse"
    assert payload["neighbors"][0]["node_id"] == "span.ui.use_property_search_query"


def test_graph_bounded_bfs_path(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    add_property_hub_graph(project)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "graph",
            "path",
            "SearchPage",
            "search_properties",
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
    assert payload["found"] is True
    assert [node["node_id"] for node in payload["nodes"]] == [
        "span.ui.property_search_page",
        "span.ui.use_property_search_query",
        "span.api.property_router.search_endpoint",
        "span.api.property_search_service.search_properties",
    ]
    assert [edge["edge_id"] for edge in payload["edges"]] == ["edge.page_to_hook", "edge.hook_to_route", "edge.route_to_service"]


def test_trace_target_resolver_reports_path_facts_evidence_and_tests(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    add_property_hub_graph(project)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "trace",
            "property_search.ui_to_api",
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
    assert payload["matched_target"]["match_type"] == "trace"
    assert payload["trace"]["trace_id"] == "trace.property_search.ui_to_api"
    assert payload["confidence"] == "high"
    assert payload["graph_path"]["found"] is True
    assert payload["graph_path"]["nodes"][0]["node_id"] == "span.ui.property_search_page"
    assert {fact["fact_id"] for fact in payload["related_facts"]} == {
        "fact.ui.property_search.page_uses_query_hook",
        "fact.api.property_search.endpoint",
        "fact.data.property_search.service_filters",
    }
    assert "api/app/routers/property.py" in payload["evidence_files"]
    assert payload["related_tests"] == ["test.property_search_flow"]
