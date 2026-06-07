from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

from ngk_framework.cli import AtlasIndexer, AtlasStore, Workspace, parse_citations
from ngk_test_helpers import ATLAS, EXPECTED_COUNTS, EXAMPLE, ROOT

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
