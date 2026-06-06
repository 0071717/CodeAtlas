#!/usr/bin/env python3
"""Export a CodeAtlas trace as ReGraph-compatible JSON.

Usage:
  python3 atlas/tools/ngk_trace_regraph_exporter.py "POST /claims"
  python3 atlas/tools/ngk_trace_regraph_exporter.py "POST /claims" --out atlas/visualizer/ngk-trace/post-claims.regraph.json

This is a file-based transformer for ngk CLI integration. It reads canonical
Atlas JSON/YAML artifacts and emits an adapter-friendly ReGraph payload.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
ATLAS = ROOT / "atlas"

COLOR = {
    "covered": "#2e7d32",
    "partial": "#f9a825",
    "untested": "#c62828",
    "ui": "#6a1b9a",
    "api": "#1565c0",
    "service": "#00838f",
    "data": "#0277bd",
    "search": "#455a64",
    "error": "#ef6c00",
    "unknown": "#757575",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: object) -> str:
    text = str(value).replace("\\", "/").strip("/")
    text = re.sub(r"[^A-Za-z0-9_./:-]+", "_", text)
    return re.sub(r"[./:-]+", "-", text).strip("-").lower() or "trace"


def read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        # CodeAtlas V2 currently writes JSON-compatible YAML. If future YAML
        # output is used, Kiro can add ruamel/PyYAML fallback here.
        return default


def write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def load_nodes() -> list[dict[str, Any]]:
    nodes = []
    nodes.extend(read(ATLAS / "graph/nodes.yaml", {}).get("nodes", []))
    for node_dir in [ATLAS / "knowledge" / "nodes"]:
        if node_dir.exists():
            for path in sorted(node_dir.glob("*.yaml")):
                data = read(path, {})
                for value in data.values():
                    if isinstance(value, list):
                        nodes.extend([x for x in value if isinstance(x, dict) and x.get("id")])
    seen = {}
    for node in nodes:
        if node.get("id"):
            seen[node["id"]] = node
    return list(seen.values())


def load_edges() -> list[dict[str, Any]]:
    edges = []
    edges.extend(read(ATLAS / "graph/edges.yaml", {}).get("edges", []))
    edges.extend(read(ATLAS / "knowledge/edges.yaml", {}).get("edges", []))
    edges.extend(read(ATLAS / "graph/error-flow-graph.yaml", {}).get("edges", []))
    edges.extend(read(ATLAS / "graph/payload-graph.yaml", {}).get("edges", []))
    seen = {}
    for edge in edges:
        if edge.get("source") and edge.get("target"):
            seen[edge.get("id") or f"edge.{edge['source']}.{edge.get('type','LINKS')}.{edge['target']}"] = edge
    return list(seen.values())


def load_flows() -> list[dict[str, Any]]:
    flows = []
    for path, key in [
        (ATLAS / "flows/api-request-flows.yaml", "api_request_flows"),
        (ATLAS / "flows/ui-action-flows.yaml", "ui_action_flows"),
        (ATLAS / "flows/error-flows.yaml", "error_flows"),
    ]:
        flows.extend(read(path, {}).get(key, []))
    return flows


def load_payloads() -> list[dict[str, Any]]:
    payloads = []
    for path, key in [
        (ATLAS / "payloads/opensearch-query-dsl.yaml", "opensearch_queries"),
        (ATLAS / "payloads/generated-query-builders.yaml", "query_builders"),
        (ATLAS / "payloads/request-payloads.yaml", "request_payloads"),
        (ATLAS / "payloads/response-payloads.yaml", "response_payloads"),
    ]:
        payloads.extend(read(path, {}).get(key, []))
    return payloads


def load_test_coverage() -> dict[str, str]:
    coverage: dict[str, str] = {}
    for path, key in [
        (ATLAS / "testing/test-inventory.yaml", "tests"),
        (ATLAS / "testing/coverage-gaps.yaml", "coverage_gaps"),
        (ATLAS / "index/test-index.yaml", "tests"),
    ]:
        data = read(path, {})
        for item in data.get(key, []):
            for target in item.get("target_nodes", []) + item.get("covers", []):
                coverage[target] = item.get("coverage_status") or item.get("quality", {}).get("coverage") or "partial"
            if item.get("id"):
                coverage[item["id"]] = item.get("coverage_status", "partial")
    return coverage


def parse_query(query: str) -> tuple[str | None, str]:
    match = re.match(r"^\s*(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s+(.+?)\s*$", query, re.I)
    if match:
        return match.group(1).upper(), match.group(2)
    return None, query.strip()


def node_matches_query(node: dict[str, Any], method: str | None, path: str) -> bool:
    candidate_path = str(node.get("path") or node.get("name") or node.get("label") or "")
    candidate_method = str(node.get("method") or "").upper()
    if method and candidate_method and method != candidate_method:
        return False
    return path in candidate_path or candidate_path in path or path in str(node.get("id", ""))


def find_start(query: str, nodes: list[dict[str, Any]], flows: list[dict[str, Any]]) -> tuple[str | None, list[str]]:
    method, path = parse_query(query)
    for flow in flows:
        trigger = flow.get("trigger", {})
        if method and str(trigger.get("method", "")).upper() != method:
            continue
        if path and path in str(trigger.get("path", "")):
            return trigger.get("endpoint") or flow.get("entrypoint"), []
    for node in nodes:
        if node_matches_query(node, method, path):
            return node.get("id"), []
    return None, [f"No Atlas node matched query: {query}"]


def traverse(start: str, edges: list[dict[str, Any]], max_depth: int) -> tuple[set[str], list[dict[str, Any]]]:
    adjacency: dict[str, list[dict[str, Any]]] = {}
    reverse: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        adjacency.setdefault(edge["source"], []).append(edge)
        reverse.setdefault(edge["target"], []).append(edge)

    selected_nodes: set[str] = {start}
    selected_edges: list[dict[str, Any]] = []
    frontier = [(start, 0)]

    while frontier:
        current, depth = frontier.pop(0)
        if depth >= max_depth:
            continue
        # Include both downstream and upstream edges so UI callers can appear
        # when the query starts at a backend endpoint.
        for edge in adjacency.get(current, []) + reverse.get(current, []):
            other = edge["target"] if edge["source"] == current else edge["source"]
            key = edge.get("id") or f"{edge['source']}->{edge['target']}"
            if not any((x.get("id") or f"{x['source']}->{x['target']}") == key for x in selected_edges):
                selected_edges.append(edge)
            if other not in selected_nodes:
                selected_nodes.add(other)
                frontier.append((other, depth + 1))
    return selected_nodes, selected_edges


def infer_kind(node: dict[str, Any]) -> str:
    text = " ".join(str(node.get(k, "")) for k in ["id", "type", "kind", "file", "name"]).lower()
    if "error" in text or "exception" in text:
        return "error"
    if "route" in text or "component" in text or "ui" in text or "react" in text:
        return "ui"
    if "endpoint" in text or "router" in text or "api" in text:
        return "api"
    if "service" in text:
        return "service"
    if "opensearch" in text or "search" in text or "query" in text:
        return "search"
    if "data" in text or "os." in text or "dao" in text:
        return "data"
    return "unknown"


def coverage_color(node_id: str, kind: str, coverage: dict[str, str]) -> str:
    status = coverage.get(node_id)
    if status in {"covered", "strong"}:
        return COLOR["covered"]
    if status in {"partial", "weak", "medium"}:
        return COLOR["partial"]
    if kind in COLOR:
        return COLOR[kind]
    return COLOR["unknown"]


def attach_payload_details(node: dict[str, Any], payloads: list[dict[str, Any]]) -> dict[str, Any]:
    node_id = node.get("id", "")
    details = {}
    for payload in payloads:
        refs = payload.get("applies_to", []) + payload.get("derived_from", []) + payload.get("target_nodes", [])
        if node_id in refs or node_id == payload.get("id") or node_id == payload.get("data_access"):
            details.setdefault("payloads", []).append(payload)
    return details


def build_regraph(query: str, max_depth: int) -> dict[str, Any]:
    nodes = load_nodes()
    edges = load_edges()
    flows = load_flows()
    payloads = load_payloads()
    coverage = load_test_coverage()
    start, missing = find_start(query, nodes, flows)

    if not start:
        return {"items": {}, "links": {}, "metadata": {"query": query, "generated_at": now(), "status": "no_match", "missing_links": missing}}

    selected_node_ids, selected_edges = traverse(start, edges, max_depth=max_depth)
    node_by_id = {node["id"]: node for node in nodes if node.get("id")}

    items: dict[str, Any] = {}
    for node_id in sorted(selected_node_ids):
        node = node_by_id.get(node_id, {"id": node_id, "type": "missing", "name": node_id})
        kind = infer_kind(node)
        payload_details = attach_payload_details(node, payloads)
        items[node_id] = {
            "label": node.get("label") or node.get("name") or node.get("path") or node_id,
            "type": kind,
            "color": coverage_color(node_id, kind, coverage),
            "data": {
                "atlas_id": node_id,
                "source": node,
                "coverage_status": coverage.get(node_id, "unknown"),
                **payload_details,
            },
        }

    links: dict[str, Any] = {}
    for index, edge in enumerate(selected_edges):
        edge_id = edge.get("id") or f"edge-{index}"
        links[edge_id] = {
            "id1": edge["source"],
            "id2": edge["target"],
            "label": edge.get("type", "LINKS"),
            "data": {"atlas_edge_id": edge_id, "source": edge},
        }

    return {
        "items": items,
        "links": links,
        "metadata": {
            "query": query,
            "start_node": start,
            "generated_at": now(),
            "max_depth": max_depth,
            "status": "ok",
            "missing_links": missing,
            "format": "adapter_friendly_regraph_payload",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export an ngk trace query as ReGraph-compatible JSON.")
    parser.add_argument("query", help='Trace query such as "POST /claims"')
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--out")
    args = parser.parse_args()

    payload = build_regraph(args.query, args.max_depth)
    out = Path(args.out) if args.out else ATLAS / "visualizer" / "ngk-trace" / f"{slug(args.query)}.regraph.json"
    write(out, payload)
    summary = out.with_suffix(".summary.md")
    summary.write_text(
        f"# ngk trace: {args.query}\n\n"
        f"Generated: {payload['metadata']['generated_at']}\n\n"
        f"Status: {payload['metadata']['status']}\n\n"
        f"Nodes: {len(payload['items'])}\n\n"
        f"Links: {len(payload['links'])}\n\n"
        f"Missing links: {payload['metadata'].get('missing_links', [])}\n",
        encoding="utf-8",
    )
    print(out)


if __name__ == "__main__":
    main()
