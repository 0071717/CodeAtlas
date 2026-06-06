#!/usr/bin/env python3
"""Build a deterministic CodeAtlas graph report.

This intentionally adopts the useful parts of Graphify's reporting model
(god-node style hubs, relationship counts, confidence summaries, suggested
questions, and a single graph.json export) without changing CodeAtlas into a
generic graph-memory tool.

Inputs are canonical CodeAtlas filesystem artifacts only. No AI, network, MCP,
or application-code execution is used.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
ATLAS = ROOT / "atlas"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_graph() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    nodes = read(ATLAS / "graph" / "nodes.json", {}).get("nodes", [])
    edges = read(ATLAS / "graph" / "edges.json", {}).get("edges", [])
    if not nodes:
        visualizer = read(ATLAS / "visualizer" / "graph-data.json", {})
        nodes = visualizer.get("nodes", [])
        edges = visualizer.get("edges", edges)
        if nodes:
            warnings.append("Loaded nodes from atlas/visualizer/graph-data.json fallback.")
    if not nodes:
        warnings.append("No graph nodes found. Run codeatlas_v2_canonical.py all first.")
    if not edges:
        warnings.append("No graph edges found. Graph report will be node-only.")
    return nodes, edges, warnings


def node_label(node: dict[str, Any]) -> str:
    return str(node.get("label") or node.get("name") or node.get("path") or node.get("function") or node.get("id"))


def adjacency(edges: list[dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    inc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if not source or not target:
            continue
        out[str(source)].append(edge)
        inc[str(target)].append(edge)
    return out, inc


def shortest_path(source: str, target: str, edges: list[dict[str, Any]], max_depth: int = 8) -> list[dict[str, Any]]:
    out, inc = adjacency(edges)
    seen = {source}
    queue: deque[tuple[str, list[dict[str, Any]]]] = deque([(source, [])])
    while queue:
        current, path = queue.popleft()
        if len(path) >= max_depth:
            continue
        for edge in out.get(current, []) + inc.get(current, []):
            other = edge["target"] if edge.get("source") == current else edge.get("source")
            if not other or other in seen:
                continue
            next_path = [*path, edge]
            if other == target:
                return next_path
            seen.add(str(other))
            queue.append((str(other), next_path))
    return []


def build_summary(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], warnings: list[str], max_items: int) -> dict[str, Any]:
    node_by_id = {str(node.get("id")): node for node in nodes if node.get("id")}
    out, inc = adjacency(edges)

    node_type_counts = Counter(str(node.get("type") or node.get("kind") or "unknown") for node in nodes)
    edge_type_counts = Counter(str(edge.get("type") or edge.get("relation") or "LINKS") for edge in edges)
    confidence_counts = Counter(str(edge.get("confidence") or "unknown") for edge in edges)

    degree_rows = []
    for node_id, node in node_by_id.items():
        degree_rows.append(
            {
                "id": node_id,
                "label": node_label(node),
                "type": node.get("type") or node.get("kind") or "unknown",
                "repo": node.get("repo"),
                "file": node.get("file"),
                "in_degree": len(inc.get(node_id, [])),
                "out_degree": len(out.get(node_id, [])),
                "degree": len(inc.get(node_id, [])) + len(out.get(node_id, [])),
            }
        )
    hubs = sorted(degree_rows, key=lambda row: (-row["degree"], str(row["id"])))[:max_items]
    orphans = [row for row in sorted(degree_rows, key=lambda row: str(row["id"])) if row["degree"] == 0][:max_items]

    broken_edges = []
    cross_repo_edges = []
    cross_file_edges = []
    for edge in edges:
        source = str(edge.get("source"))
        target = str(edge.get("target"))
        source_node = node_by_id.get(source)
        target_node = node_by_id.get(target)
        if not source_node or not target_node:
            broken_edges.append({"id": edge.get("id"), "source": source, "target": target, "type": edge.get("type")})
            continue
        if source_node.get("repo") and target_node.get("repo") and source_node.get("repo") != target_node.get("repo"):
            cross_repo_edges.append(edge)
        elif source_node.get("file") and target_node.get("file") and source_node.get("file") != target_node.get("file"):
            cross_file_edges.append(edge)

    endpoints = [node for node in nodes if str(node.get("type", "")).lower() == "endpoint"]
    routes = [node for node in nodes if str(node.get("type", "")).lower() == "route"]
    suggested_questions = [
        "Which endpoints have no mapped frontend API client?",
        "Which API clients do not map to a backend endpoint?",
        "Which low-confidence edges should be reviewed first?",
        "Which nodes are orphaned or disconnected from flows?",
    ]
    if endpoints:
        suggested_questions.append("Show the trace for the highest-degree endpoint node.")
    if routes:
        suggested_questions.append("Which React routes connect to backend endpoints through API clients?")

    return {
        "generated_at": now(),
        "status": "ok" if nodes else "empty",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_type_counts": dict(sorted(node_type_counts.items())),
        "edge_type_counts": dict(sorted(edge_type_counts.items())),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "hubs": hubs,
        "orphans": orphans,
        "broken_edges": broken_edges[:max_items],
        "broken_edge_count": len(broken_edges),
        "cross_repo_edge_count": len(cross_repo_edges),
        "cross_file_edge_count": len(cross_file_edges),
        "cross_file_examples": [
            {"id": e.get("id"), "source": e.get("source"), "target": e.get("target"), "type": e.get("type"), "confidence": e.get("confidence")}
            for e in cross_file_edges[:max_items]
        ],
        "suggested_questions": suggested_questions,
        "warnings": warnings,
    }


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "_None._\n"
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")
    return "\n".join(out) + "\n"


def build_markdown(summary: dict[str, Any]) -> str:
    hub_rows = [[h["id"], h["type"], h["degree"], h["repo"] or "", h["file"] or ""] for h in summary["hubs"]]
    orphan_rows = [[h["id"], h["type"], h["repo"] or "", h["file"] or ""] for h in summary["orphans"]]
    broken_rows = [[e.get("id"), e.get("type"), e.get("source"), e.get("target")] for e in summary["broken_edges"]]
    question_lines = "\n".join(f"- {q}" for q in summary["suggested_questions"])
    warning_lines = "\n".join(f"- {w}" for w in summary["warnings"]) or "- None"
    node_counts = "\n".join(f"- `{k}`: {v}" for k, v in summary["node_type_counts"].items()) or "- None"
    edge_counts = "\n".join(f"- `{k}`: {v}" for k, v in summary["edge_type_counts"].items()) or "- None"
    confidence_counts = "\n".join(f"- `{k}`: {v}" for k, v in summary["confidence_counts"].items()) or "- None"
    return f"""# CodeAtlas Graph Report

Generated: {summary['generated_at']}

Status: `{summary['status']}`

## Summary

- Nodes: {summary['node_count']}
- Edges: {summary['edge_count']}
- Broken edges: {summary['broken_edge_count']}
- Cross-repo edges: {summary['cross_repo_edge_count']}
- Cross-file edges: {summary['cross_file_edge_count']}

## Node types

{node_counts}

## Edge types

{edge_counts}

## Edge confidence

{confidence_counts}

## Hub nodes

{markdown_table(['ID', 'Type', 'Degree', 'Repo', 'File'], hub_rows)}

## Orphan nodes

{markdown_table(['ID', 'Type', 'Repo', 'File'], orphan_rows)}

## Broken edges

{markdown_table(['ID', 'Type', 'Source', 'Target'], broken_rows)}

## Suggested questions

{question_lines}

## Warnings

{warning_lines}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic CodeAtlas graph report.")
    parser.add_argument("--out-dir", default="atlas/visualizer", help="Directory for GRAPH_REPORT.md, graph-report.json, and graph.json")
    parser.add_argument("--max-items", type=int, default=20)
    args = parser.parse_args()

    nodes, edges, warnings = load_graph()
    summary = build_summary(nodes, edges, warnings, args.max_items)
    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "graph-report.json", summary)
    write_json(out_dir / "graph.json", {"generated_at": summary["generated_at"], "nodes": nodes, "edges": edges})
    (out_dir / "GRAPH_REPORT.md").write_text(build_markdown(summary), encoding="utf-8")
    print(f"graph-report nodes={summary['node_count']} edges={summary['edge_count']} broken={summary['broken_edge_count']}")
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
