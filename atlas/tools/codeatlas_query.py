#!/usr/bin/env python3
"""Query CodeAtlas artifacts from the terminal.

This is a small Graphify-inspired query/path/explain surface, but it reads only
CodeAtlas deterministic artifacts. It is meant to support `ngk ask`, `ngk trace`,
and Kiro pre-flight exploration without re-reading the whole target codebase.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
ATLAS = ROOT / "atlas"


def candidate_paths(path: Path) -> list[Path]:
    if path.suffix == ".yaml":
        return [path.with_suffix(".json"), path]
    if path.suffix == ".json":
        return [path, path.with_suffix(".yaml")]
    return [path]


def read(path: Path, default: Any) -> Any:
    for candidate in candidate_paths(path):
        if not candidate.exists():
            continue
        try:
            return json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def load_graph() -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    nodes = read(ATLAS / "graph" / "nodes.json", {}).get("nodes", [])
    edges = read(ATLAS / "graph" / "edges.json", {}).get("edges", [])
    if not nodes:
        visualizer = read(ATLAS / "visualizer" / "graph-data.json", {})
        nodes = visualizer.get("nodes", [])
        edges = visualizer.get("edges", edges)
    node_by_id = {str(node.get("id")): node for node in nodes if node.get("id")}
    return node_by_id, edges


def node_text(node: dict[str, Any]) -> str:
    fields = ["id", "type", "kind", "name", "path", "function", "file", "repo"]
    return " ".join(str(node.get(field, "")) for field in fields).lower()


def edge_text(edge: dict[str, Any]) -> str:
    fields = ["id", "type", "relation", "source", "target", "confidence"]
    return " ".join(str(edge.get(field, "")) for field in fields).lower()


def score_text(text: str, terms: list[str]) -> int:
    score = 0
    for term in terms:
        if term in text:
            score += 3
        for token in text.replace(".", " ").replace("/", " ").replace("_", " ").split():
            if term == token:
                score += 2
    return score


def find_nodes(query: str, limit: int) -> list[tuple[int, dict[str, Any]]]:
    node_by_id, _ = load_graph()
    terms = [term.lower() for term in query.split() if term.strip()]
    if not terms:
        return []
    matches = []
    for node in node_by_id.values():
        score = score_text(node_text(node), terms)
        if score:
            matches.append((score, node))
    return sorted(matches, key=lambda item: (-item[0], str(item[1].get("id"))))[:limit]


def resolve_node(query: str) -> str | None:
    node_by_id, _ = load_graph()
    if query in node_by_id:
        return query
    matches = find_nodes(query, 1)
    return str(matches[0][1].get("id")) if matches else None


def neighbors(node_id: str, edges: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    result = []
    for edge in edges:
        if edge.get("source") == node_id or edge.get("target") == node_id:
            result.append(edge)
    return sorted(result, key=lambda e: str(e.get("id")))[:limit]


def print_query(args: argparse.Namespace) -> int:
    matches = find_nodes(args.text, args.limit)
    if args.json:
        print(json.dumps({"query": args.text, "matches": [{"score": s, "node": n} for s, n in matches]}, indent=2))
        return 0 if matches else 1
    if not matches:
        print(f"No CodeAtlas nodes matched: {args.text}")
        return 1
    for score, node in matches:
        label = node.get("name") or node.get("path") or node.get("function") or node.get("id")
        print(f"[{score}] {node.get('id')}  type={node.get('type')}  label={label}  file={node.get('file')}")
    return 0


def print_explain(args: argparse.Namespace) -> int:
    node_by_id, edges = load_graph()
    node_id = resolve_node(args.node)
    if not node_id:
        print(f"No CodeAtlas node matched: {args.node}")
        return 1
    node = node_by_id[node_id]
    neigh = neighbors(node_id, edges, args.limit)
    if args.json:
        print(json.dumps({"node": node, "neighbors": neigh}, indent=2))
        return 0
    print(f"# {node_id}\n")
    for key in ["type", "repo", "file", "name", "path", "function"]:
        if node.get(key) is not None:
            print(f"- {key}: {node.get(key)}")
    print("\n## Neighbor edges")
    if not neigh:
        print("_None._")
    for edge in neigh:
        direction = "out" if edge.get("source") == node_id else "in"
        other = edge.get("target") if direction == "out" else edge.get("source")
        print(f"- {direction}: {edge.get('type', 'LINKS')} -> {other} ({edge.get('confidence', 'unknown')})")
    return 0


def build_adjacency(edges: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    adjacency: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if not source or not target:
            continue
        adjacency[str(source)].append(edge)
        if not edge.get("directed", True):
            adjacency[str(target)].append({**edge, "source": target, "target": source})
    return adjacency


def shortest_path(source: str, target: str, edges: list[dict[str, Any]], max_depth: int) -> list[dict[str, Any]]:
    adjacency = build_adjacency(edges)
    queue: deque[tuple[str, list[dict[str, Any]]]] = deque([(source, [])])
    seen = {source}
    while queue:
        current, path = queue.popleft()
        if len(path) >= max_depth:
            continue
        for edge in adjacency.get(current, []):
            next_node = str(edge.get("target"))
            if next_node in seen:
                continue
            next_path = [*path, edge]
            if next_node == target:
                return next_path
            seen.add(next_node)
            queue.append((next_node, next_path))
    return []


def print_path(args: argparse.Namespace) -> int:
    node_by_id, edges = load_graph()
    source = resolve_node(args.source)
    target = resolve_node(args.target)
    if not source or not target:
        print(json.dumps({"source": source, "target": target, "status": "no_match"}, indent=2) if args.json else "Could not resolve source or target node.")
        return 1
    path = shortest_path(source, target, edges, args.max_depth)
    payload = {"source": source, "target": target, "status": "ok" if path else "no_path", "edges": path}
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0 if path else 1
    if not path:
        print(f"No path found from {source} to {target} within depth {args.max_depth}.")
        return 1
    current = source
    print(current)
    for edge in path:
        print(f"  --{edge.get('type', 'LINKS')}[{edge.get('confidence', 'unknown')}]--> {edge.get('target')}")
        current = str(edge.get("target"))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Query deterministic CodeAtlas graph artifacts.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("query", help="Search nodes by text")
    q.add_argument("text")
    q.add_argument("--limit", type=int, default=20)
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=print_query)

    e = sub.add_parser("explain", help="Show one node and its neighbor edges")
    e.add_argument("node")
    e.add_argument("--limit", type=int, default=40)
    e.add_argument("--json", action="store_true")
    e.set_defaults(func=print_explain)

    p = sub.add_parser("path", help="Find a directed path between two nodes")
    p.add_argument("source")
    p.add_argument("target")
    p.add_argument("--max-depth", type=int, default=8)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=print_path)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
