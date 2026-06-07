from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "ngk-property-hub"
ATLAS = EXAMPLE / ".atlas"
EXPECTED_COUNTS = {"facts": 3, "evidence": 4, "spans": 4, "traces": 1, "nodes": 0, "edges": 0, "retrieval_items": 8}

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

def write_answer_session(ngk_dir: Path, session_id: str, text: str) -> Path:
    session = ngk_dir / "sessions" / session_id
    session.mkdir(parents=True, exist_ok=True)
    (session / "kiro-output.raw.md").write_text(text, encoding="utf-8")
    (ngk_dir / "sessions" / "latest").write_text(session_id, encoding="utf-8")
    return session

def add_contract_artifacts(project: Path) -> None:
    contracts = project / ".atlas" / "contracts"
    contracts.mkdir(parents=True, exist_ok=True)
    (contracts / "openapi.json").write_text(json.dumps({"paths": {"/properties/search": {"get": {}}}}), encoding="utf-8")
    (contracts / "api_client_calls.jsonl").write_text('{"path":"ui/src/api/propertyClient.ts","operation":"GET /properties/search"}\n', encoding="utf-8")
    (contracts / "query_hooks.jsonl").write_text('{"hook":"usePropertySearchQuery","operation":"GET /properties/search"}\n', encoding="utf-8")
    (contracts / "pydantic_models.jsonl").write_text('{"model":"PropertySearchResult","fields":["location","bedrooms"]}\n', encoding="utf-8")
    (contracts / "opensearch_fields.jsonl").write_text('{"index":"properties","fields":["location","bedrooms"]}\n', encoding="utf-8")

