"""Compatibility smoke tests for legacy ngk_framework.cli imports."""
from __future__ import annotations

from ngk_framework.cli import AtlasIndexer, AtlasStore, Workspace, file_hash_candidates, main, parse_citations
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_cli_compatibility_exports() -> None:
    assert AtlasIndexer is not None
    assert AtlasStore is not None
    assert Workspace is not None
    assert file_hash_candidates is not None
    assert main is not None
    parsed = parse_citations('[fact.api.property_search.endpoint]')
    assert parsed["fact_ids"] == ["fact.api.property_search.endpoint"]
ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "ngk-property-hub"
ATLAS = EXAMPLE / ".atlas"
EXPECTED_COUNTS = {"facts": 3, "evidence": 4, "spans": 4, "traces": 1, "nodes": 0, "edges": 0, "retrieval_items": 8}


def test_indexer_loads_property_hub(tmp_path: Path) -> None:
    ws = Workspace(ROOT, str(ATLAS), str(tmp_path / ".ngk"))
    counts = AtlasIndexer(ws).index()
    assert counts == EXPECTED_COUNTS

    for cache_name in ["citation_index.jsonl", "source_cards.jsonl", "retrieval_index.jsonl", "trace_cards.jsonl"]:
        assert (ws.cache / cache_name).exists()

    with sqlite3.connect(ws.db) as conn:
        for table, expected in [
            ("facts", 3),
            ("evidence", 4),
            ("source_spans", 4),
            ("traces", 1),
            ("nodes", 0),
            ("edges", 0),
            ("retrieval_items", 8),
        ]:
            assert conn.execute(f"select count(*) from {table}").fetchone()[0] == expected

    rows = AtlasStore(ws).search_facts("property search")
    assert [row["fact_id"] for row in rows]
    assert "fact.api.property_search.endpoint" in {row["fact_id"] for row in rows}


def test_parse_citations_prefers_atlas_block() -> None:
    parsed = parse_citations(
        '<atlas_citations>{"citations":[{"fact_id":"fact.api.property_search.endpoint"}]}</atlas_citations>'
    )
    assert parsed["format"] == "atlas_citations"
    assert parsed["fact_ids"] == ["fact.api.property_search.endpoint"]


def test_cli_accepts_nested_atlas_index(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "atlas",
            "index",
            "--atlas",
            str(ATLAS),
            "--ngk-dir",
            str(tmp_path / ".ngk"),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(result.stdout) == EXPECTED_COUNTS


def test_sources_searches_paths_traces_and_routes(tmp_path: Path) -> None:
    ws = Workspace(ROOT, str(ATLAS), str(tmp_path / ".ngk"))
    AtlasIndexer(ws).index()

    path_hits = AtlasStore(ws).search("SearchPage.tsx")
    assert any(row["item_type"] == "fact" and row["fact_id"] == "fact.ui.property_search.page_uses_query_hook" for row in path_hits)

    trace_hits = AtlasStore(ws).search("ui_to_api")
    assert any(row["item_type"] == "trace" and row["trace_id"] == "trace.property_search.ui_to_api" for row in trace_hits)

    route_result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "sources",
            "GET /properties/search",
            "--atlas",
            str(ATLAS),
            "--ngk-dir",
            str(tmp_path / ".ngk"),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert any(row["fact_id"] == "fact.api.property_search.endpoint" for row in json.loads(route_result.stdout) if row.get("fact_id"))


def test_fact_show_yaml_code_include_evidence_and_related_traces(tmp_path: Path) -> None:
    ngk_dir = tmp_path / ".ngk"
    base = ["--atlas", str(ATLAS), "--ngk-dir", str(ngk_dir)]
    subprocess.run([sys.executable, str(ROOT / "atlas" / "tools" / "ngk_cli.py"), "atlas", "index", *base], cwd=ROOT, check=True, capture_output=True, text=True)

    show = subprocess.run(
        [sys.executable, str(ROOT / "atlas" / "tools" / "ngk_cli.py"), "fact", "show", "fact.api.property_search.endpoint", *base, "--json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(show.stdout)
    assert payload["fact"]["claim"] == "The backend exposes GET /properties/search for property search."
    assert payload["evidence"][0]["source_span"]["span_id"] == "span.api.property_router.search_endpoint"
    assert payload["related_traces"][0]["trace_id"] == "trace.property_search.ui_to_api"

    yaml_result = subprocess.run(
        [sys.executable, str(ROOT / "atlas" / "tools" / "ngk_cli.py"), "fact", "yaml", "fact.api.property_search.endpoint", *base],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "GET /properties/search" in yaml_result.stdout

    code_result = subprocess.run(
        [sys.executable, str(ROOT / "atlas" / "tools" / "ngk_cli.py"), "fact", "code", "fact.api.property_search.endpoint", *base],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "api/app/routers/property.py:8-14" in code_result.stdout
    assert "@router.get" in code_result.stdout


def test_indexer_reads_optional_graph_and_extra_indexes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    atlas = project / ".atlas"
    (atlas / "graph").mkdir()
    (atlas / "graph" / "nodes.jsonl").write_text('{"node_id":"symbol.ui.SearchPage","label":"SearchPage","kind":"react_component","path":"ui/src/features/property/SearchPage.tsx"}\n', encoding="utf-8")
    (atlas / "graph" / "edges.jsonl").write_text('{"edge_id":"edge.ui_to_api","from":"symbol.ui.SearchPage","to":"api.GET./properties/search","type":"calls","confidence":"high","fact_ids":["fact.api.property_search.endpoint"]}\n', encoding="utf-8")
    (atlas / "indexes" / "routes.jsonl").write_text('{"item_id":"route.property_search","item_type":"route","title":"GET /properties/search","text":"backend property search route","route":"GET /properties/search","fact_id":"fact.api.property_search.endpoint"}\n', encoding="utf-8")

    ws = Workspace(project, ".atlas", str(tmp_path / ".ngk"))
    counts = AtlasIndexer(ws).index()
    assert counts["nodes"] == 1
    assert counts["edges"] == 1
    assert counts["retrieval_items"] == 11
    assert any(row["item_type"] == "route" for row in AtlasStore(ws).search("GET /properties/search"))


def test_indexer_degrades_when_optional_artifacts_are_missing(tmp_path: Path) -> None:
    project = tmp_path / "minimal"
    (project / ".atlas" / "facts").mkdir(parents=True)
    (project / ".atlas" / "facts" / "facts.json").write_text(
        json.dumps({"facts": [{"id": "fact.minimal", "claim": "Minimal fact indexes.", "confidence": "low"}]}),
        encoding="utf-8",
    )
    ws = Workspace(project, ".atlas", ".ngk")
    assert AtlasIndexer(ws).index() == {"facts": 1, "evidence": 0, "spans": 0, "traces": 0, "nodes": 0, "edges": 0, "retrieval_items": 1}
    assert AtlasStore(ws).search("Minimal")


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


def add_property_hub_graph(project: Path) -> None:
    atlas = project / ".atlas"
    (atlas / "graph").mkdir(exist_ok=True)
    nodes = [
        {"node_id": "span.ui.property_search_page", "label": "SearchPage", "kind": "react_component", "path": "ui/src/features/property/SearchPage.tsx"},
        {"node_id": "span.ui.use_property_search_query", "label": "usePropertySearchQuery", "kind": "react_hook", "path": "ui/src/features/property/usePropertySearchQuery.ts"},
        {"node_id": "span.api.property_router.search_endpoint", "label": "GET /properties/search", "kind": "api_endpoint", "path": "api/app/routers/property.py"},
        {"node_id": "span.api.property_search_service.search_properties", "label": "search_properties", "kind": "function", "path": "api/app/services/property_search.py"},
    ]
    edges = [
        {"edge_id": "edge.page_to_hook", "from": "span.ui.property_search_page", "to": "span.ui.use_property_search_query", "type": "calls", "confidence": "high", "fact_ids": ["fact.ui.property_search.page_uses_query_hook"]},
        {"edge_id": "edge.hook_to_route", "from": "span.ui.use_property_search_query", "to": "span.api.property_router.search_endpoint", "type": "calls_api", "confidence": "high", "fact_ids": ["fact.api.property_search.endpoint"]},
        {"edge_id": "edge.route_to_service", "from": "span.api.property_router.search_endpoint", "to": "span.api.property_search_service.search_properties", "type": "delegates", "confidence": "high", "fact_ids": ["fact.data.property_search.service_filters"]},
    ]
    (atlas / "graph" / "nodes.jsonl").write_text("".join(json.dumps(row) + "\n" for row in nodes), encoding="utf-8")
    (atlas / "graph" / "edges.jsonl").write_text("".join(json.dumps(row) + "\n" for row in edges), encoding="utf-8")
    trace_path = atlas / "traces" / "flow_traces.jsonl"
    trace = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[0])
    trace["related_tests"] = ["test.property_search_flow"]
    trace_path.write_text(json.dumps(trace) + "\n", encoding="utf-8")


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


def add_property_hub_test_artifacts(project: Path) -> None:
    add_property_hub_graph(project)
    test_path = project / "ui" / "src" / "features" / "property" / "SearchPage.test.tsx"
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text("import { SearchPage } from './SearchPage';\n", encoding="utf-8")
    atlas = project / ".atlas"
    nodes_path = atlas / "graph" / "nodes.jsonl"
    with nodes_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"node_id": "test.ui.SearchPage", "label": "SearchPage test", "kind": "test", "path": "ui/src/features/property/SearchPage.test.tsx"}) + "\n")
    edges_path = atlas / "graph" / "edges.jsonl"
    with edges_path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "edge_id": "edge.test_covers_page_fact",
                    "from": "test.ui.SearchPage",
                    "to": "span.ui.property_search_page",
                    "type": "test_covers",
                    "confidence": "high",
                    "fact_ids": ["fact.ui.property_search.page_uses_query_hook"],
                }
            )
            + "\n"
        )


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


def test_ctx_build_creates_evidence_backed_context_pack_and_explain(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    add_property_hub_graph(project)
    base = ["--atlas", str(project / ".atlas"), "--ngk-dir", str(tmp_path / ".ngk")]
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "ctx",
            "build",
            "ask",
            "How does property search flow from UI to API?",
            *base,
            "--limit",
            "5",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    context_path = Path(result.stdout.strip())
    text = context_path.read_text(encoding="utf-8")
    assert "## User task" in text
    assert "## Atlas drift status" in text
    assert "## Selected facts" in text
    assert "fact.api.property_search.endpoint" in text
    assert "api/app/routers/property.py:8-14" in text
    assert "## Selected traces" in text
    assert "trace.property_search.ui_to_api" in text
    assert "## Related tests" in text
    assert "## Known gaps" in text
    assert "## Strict Kiro citation rules" in text
    assert "<atlas_citations>" in text

    payload = json.loads((context_path.parent / "context-pack.json").read_text(encoding="utf-8"))
    assert payload["drift"]["status"] in {"clean", "drift"}
    assert payload["facts"][0]["selection_reason"]
    assert payload["facts"][0]["evidence"]
    assert payload["traces"]

    explain = subprocess.run(
        [sys.executable, str(ROOT / "atlas" / "tools" / "ngk_cli.py"), "ctx", "explain", "latest", *base, "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    explanation = json.loads(explain.stdout)
    assert explanation["facts"]
    assert explanation["traces"]
    assert any("matched user task" in fact["reason"] for fact in explanation["facts"])


def test_ask_no_agent_writes_context_pack_without_kiro(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "ask",
            "What endpoint powers property search?",
            "--atlas",
            str(ATLAS),
            "--ngk-dir",
            str(tmp_path / ".ngk"),
            "--no-agent",
            "--limit",
            "3",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    prefix = "Context pack: "
    assert prefix in result.stdout
    context_path = Path(result.stdout.strip().split(prefix, 1)[1])
    assert context_path.exists()
    text = context_path.read_text(encoding="utf-8")
    assert "The backend exposes GET /properties/search" in text
    assert "Required <atlas_citations> JSON schema" in text
    assert not (context_path.parent / "kiro-output.raw.md").exists()


def write_answer_session(ngk_dir: Path, session_id: str, text: str) -> Path:
    session = ngk_dir / "sessions" / session_id
    session.mkdir(parents=True, exist_ok=True)
    (session / "kiro-output.raw.md").write_text(text, encoding="utf-8")
    (ngk_dir / "sessions" / "latest").write_text(session_id, encoding="utf-8")
    return session


def test_verify_answer_accepts_good_block_and_preserves_not_confirmed(tmp_path: Path) -> None:
    ngk_dir = tmp_path / ".ngk"
    write_answer_session(
        ngk_dir,
        "good",
        """
The backend exposes the property search endpoint.
<atlas_citations>{
  "claims": [
    {"claim_id": "claim.1", "text": "Property search has an API endpoint.", "support": "supported", "fact_ids": ["fact.api.property_search.endpoint"]}
  ],
  "citations": [{"fact_id": "fact.api.property_search.endpoint", "used_for_claims": ["claim.1"]}],
  "not_confirmed": [{"claim_id": "claim.2", "text": "Latency is under 10ms.", "reason": "No Atlas fact confirms latency."}]
}</atlas_citations>
""",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "verify-answer",
            "latest",
            "--atlas",
            str(ATLAS),
            "--ngk-dir",
            str(ngk_dir),
            "--json",
            "--strict",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    audit = json.loads(result.stdout)
    assert audit["status"] == "passed"
    assert audit["resolved_fact_ids"] == ["fact.api.property_search.endpoint"]
    assert audit["not_confirmed"][0]["claim_id"] == "claim.2"
    assert audit["unsupported_claims"] == []


def test_verify_answer_reports_missing_and_hallucinated_citations(tmp_path: Path) -> None:
    ngk_dir = tmp_path / ".ngk"
    write_answer_session(
        ngk_dir,
        "bad",
        '<atlas_citations>{"claims":[{"claim_id":"claim.1","text":"A hallucinated fact supports this.","support":"supported","fact_ids":["fact.missing.hallucinated"]}],"citations":[{"fact_id":"fact.missing.hallucinated"}],"not_confirmed":[]}</atlas_citations>',
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "verify-answer",
            "bad",
            "--atlas",
            str(ATLAS),
            "--ngk-dir",
            str(ngk_dir),
            "--json",
            "--strict",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 6
    audit = json.loads(result.stdout)
    assert audit["status"] == "failed"
    assert audit["missing_fact_ids"] == ["fact.missing.hallucinated"]
    assert audit["unsupported_claims"][0]["claim_id"] == "claim.1"


def test_verify_answer_supports_inline_and_fallback_fact_scanning(tmp_path: Path) -> None:
    inline = parse_citations("The endpoint exists [fact.api.property_search.endpoint].")
    fallback = parse_citations("The endpoint exists fact.api.property_search.endpoint.")
    assert inline["format"] == "inline_brackets"
    assert inline["fact_ids"] == ["fact.api.property_search.endpoint"]
    assert fallback["format"] == "fallback_scan"
    assert fallback["fact_ids"] == ["fact.api.property_search.endpoint"]


def test_verify_answer_reports_stale_cited_source(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-c", "user.email=ngk@example.com", "-c", "user.name=ngk", "commit", "-m", "baseline"],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    route = project / "api" / "app" / "routers" / "property.py"
    route.write_text(route.read_text(encoding="utf-8") + "\n# stale\n", encoding="utf-8")
    ngk_dir = tmp_path / ".ngk"
    write_answer_session(
        ngk_dir,
        "stale",
        '<atlas_citations>{"claims":[{"claim_id":"claim.1","text":"The route exists.","support":"supported","fact_ids":["fact.api.property_search.endpoint"]}],"citations":[{"fact_id":"fact.api.property_search.endpoint"}],"not_confirmed":[]}</atlas_citations>',
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "verify-answer",
            "stale",
            "--atlas",
            str(project / ".atlas"),
            "--ngk-dir",
            str(ngk_dir),
            "--json",
            "--strict",
        ],
        cwd=project,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 6
    audit = json.loads(result.stdout)
    assert audit["stale_fact_ids"] == ["fact.api.property_search.endpoint"]
    assert "cited facts have stale sources" in audit["unsupported_claims"][0]["reasons"][-1]


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


def add_contract_artifacts(project: Path) -> None:
    contracts = project / ".atlas" / "contracts"
    contracts.mkdir(parents=True, exist_ok=True)
    (contracts / "openapi.json").write_text(json.dumps({"paths": {"/properties/search": {"get": {}}}}), encoding="utf-8")
    (contracts / "api_client_calls.jsonl").write_text('{"path":"ui/src/api/propertyClient.ts","operation":"GET /properties/search"}\n', encoding="utf-8")
    (contracts / "query_hooks.jsonl").write_text('{"hook":"usePropertySearchQuery","operation":"GET /properties/search"}\n', encoding="utf-8")
    (contracts / "pydantic_models.jsonl").write_text('{"model":"PropertySearchResult","fields":["location","bedrooms"]}\n', encoding="utf-8")
    (contracts / "opensearch_fields.jsonl").write_text('{"index":"properties","fields":["location","bedrooms"]}\n', encoding="utf-8")


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
