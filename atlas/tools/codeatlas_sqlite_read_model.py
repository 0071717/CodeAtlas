#!/usr/bin/env python3
"""Compile CodeAtlas artifacts into a no-MCP SQLite read model.

JSON/YAML artifacts remain canonical. `atlas/knowledge/atlas.sqlite` is a fast
local query layer for `ngk`, Kiro wrappers, and context-pack generation.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
ATLAS = ROOT / "atlas"
DB = ATLAS / "knowledge" / "atlas.sqlite"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def candidates(path: Path) -> list[Path]:
    if path.suffix == ".json":
        return [path, path.with_suffix(".yaml")]
    if path.suffix == ".yaml":
        return [path.with_suffix(".json"), path]
    return [path]


def read(path: Path, default: Any) -> Any:
    for candidate in candidates(path):
        if candidate.exists():
            try:
                return json.loads(candidate.read_text(encoding="utf-8"))
            except Exception:
                return default
    return default


def write(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_index_nodes() -> list[dict[str, Any]]:
    specs = [
        ("symbol", "symbol-index.json", "symbols"),
        ("endpoint", "endpoint-index.json", "endpoints"),
        ("api_client", "api-client-index.json", "api_clients"),
        ("route", "route-index.json", "routes"),
        ("component", "component-index.json", "components"),
        ("hook", "hook-index.json", "hooks"),
        ("schema", "schema-index.json", "schemas"),
        ("service", "service-index.json", "services"),
        ("data_access", "data-access-index.json", "data_access"),
        ("runtime", "runtime-entrypoint-index.json", "runtime_entrypoints"),
        ("test", "test-index.json", "tests"),
        ("config", "config-index.json", "configs"),
    ]
    nodes: list[dict[str, Any]] = []
    for typ, filename, key in specs:
        for item in read(ATLAS / "index" / filename, {}).get(key, []):
            if item.get("id"):
                nodes.append({
                    "id": item.get("id"),
                    "type": typ,
                    "repo": item.get("repo"),
                    "file": item.get("file"),
                    "name": item.get("name") or item.get("path") or item.get("function") or item.get("handler"),
                    "raw": item,
                })
    return nodes


def load_nodes_edges() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes = read(ATLAS / "graph" / "nodes.json", {}).get("nodes", [])
    edges = read(ATLAS / "graph" / "edges.json", {}).get("edges", [])
    if not nodes:
        graph = read(ATLAS / "visualizer" / "graph-data.json", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", edges)
    if not nodes:
        nodes = load_index_nodes()
    return nodes, edges


def load_facts() -> list[dict[str, Any]]:
    return read(ATLAS / "facts" / "technical-facts.json", {}).get("technical_facts", [])


def load_flows() -> list[dict[str, Any]]:
    flows: list[dict[str, Any]] = []
    for rel, key, typ in [
        ("api-request-flows.json", "api_request_flows", "api_request_flow"),
        ("ui-flows.json", "ui_flows", "ui_flow"),
    ]:
        for flow in read(ATLAS / "flows" / rel, {}).get(key, []):
            flows.append({**flow, "type": typ})
    for flow in read(ATLAS / "errors" / "error-flow-index.json", {}).get("error_flows", []):
        flows.append({**flow, "type": "error_flow"})
    return flows


def load_gaps() -> list[dict[str, Any]]:
    return read(ATLAS / "audit" / "capability-gaps.json", {}).get("capability_gaps", [])


def node_title(node: dict[str, Any]) -> str:
    raw = node.get("raw") if isinstance(node.get("raw"), dict) else {}
    return str(node.get("name") or raw.get("name") or raw.get("path") or raw.get("function") or raw.get("handler") or node.get("id"))


def node_text(node: dict[str, Any]) -> str:
    raw = node.get("raw") if isinstance(node.get("raw"), dict) else node
    parts = [
        node.get("id"), node.get("type"), node.get("repo"), node.get("file"),
        node.get("name"), raw.get("path"), raw.get("function"), raw.get("handler"), raw.get("signature")
    ]
    return " ".join(str(x) for x in parts if x)


def main() -> int:
    nodes, edges = load_nodes_edges()
    facts = load_facts()
    flows = load_flows()
    gaps = load_gaps()

    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript("""
    CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE nodes(id TEXT PRIMARY KEY, type TEXT, repo TEXT, file TEXT, name TEXT, text TEXT, json TEXT NOT NULL);
    CREATE TABLE edges(id TEXT PRIMARY KEY, source TEXT, target TEXT, type TEXT, confidence TEXT, needs_review INTEGER, json TEXT NOT NULL);
    CREATE INDEX idx_edges_source ON edges(source);
    CREATE INDEX idx_edges_target ON edges(target);
    CREATE TABLE facts(id TEXT PRIMARY KEY, type TEXT, source_id TEXT, repo TEXT, file TEXT, statement TEXT, confidence TEXT, needs_review INTEGER, json TEXT NOT NULL);
    CREATE TABLE flows(id TEXT PRIMARY KEY, type TEXT, trigger TEXT, text TEXT, confidence TEXT, needs_review INTEGER, json TEXT NOT NULL);
    CREATE TABLE capability_gaps(id TEXT PRIMARY KEY, import_root TEXT, risk TEXT, file_count INTEGER, import_count INTEGER, text TEXT, json TEXT NOT NULL);
    CREATE TABLE cards(id TEXT PRIMARY KEY, kind TEXT, node_id TEXT, title TEXT, body TEXT, confidence TEXT, needs_review INTEGER, json TEXT NOT NULL);
    """)

    generated = now()
    conn.execute("INSERT INTO metadata VALUES (?, ?)", ("generated_at", generated))
    conn.execute("INSERT INTO metadata VALUES (?, ?)", ("mcp_required", "false"))
    conn.execute("INSERT INTO metadata VALUES (?, ?)", ("source_of_truth", "atlas JSON/YAML artifacts"))

    seen: set[str] = set()
    for node in nodes:
        node_id = str(node.get("id") or "")
        if not node_id or node_id in seen:
            continue
        seen.add(node_id)
        title = node_title(node)
        body = node_text(node)
        conn.execute("INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?)", (
            node_id, node.get("type"), node.get("repo"), node.get("file"), title, body, json.dumps(node, sort_keys=True)
        ))
        conn.execute("INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
            f"card.node.{node_id}", "node", node_id, title, body, node.get("confidence"), int(bool(node.get("needs_review", False))), json.dumps({"node": node}, sort_keys=True)
        ))

    for i, edge in enumerate(edges):
        edge_id = str(edge.get("id") or f"edge.generated.{i}")
        conn.execute("INSERT OR REPLACE INTO edges VALUES (?, ?, ?, ?, ?, ?, ?)", (
            edge_id, edge.get("source"), edge.get("target"), edge.get("type"), edge.get("confidence"), int(bool(edge.get("needs_review", False))), json.dumps(edge, sort_keys=True)
        ))

    for fact in facts:
        fact_id = str(fact.get("id") or "")
        if not fact_id:
            continue
        statement = str(fact.get("statement", ""))
        conn.execute("INSERT OR REPLACE INTO facts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (
            fact_id, fact.get("type"), fact.get("source_id"), fact.get("repo"), fact.get("file"), statement, fact.get("confidence"), int(bool(fact.get("needs_review", False))), json.dumps(fact, sort_keys=True)
        ))
        conn.execute("INSERT OR REPLACE INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
            f"card.fact.{fact_id}", "fact", fact.get("source_id"), statement[:120] or fact_id, statement, fact.get("confidence"), int(bool(fact.get("needs_review", False))), json.dumps({"fact": fact}, sort_keys=True)
        ))

    for flow in flows:
        flow_id = str(flow.get("id") or "")
        if not flow_id:
            continue
        trigger = json.dumps(flow.get("trigger") or flow.get("route") or flow.get("source") or {}, sort_keys=True)
        body = " ".join([flow_id, str(flow.get("type", "")), trigger, json.dumps(flow.get("steps", []), sort_keys=True), json.dumps(flow.get("error_exits", []), sort_keys=True)])
        conn.execute("INSERT OR REPLACE INTO flows VALUES (?, ?, ?, ?, ?, ?, ?)", (
            flow_id, flow.get("type"), trigger, body, flow.get("confidence"), int(bool(flow.get("needs_review", False))), json.dumps(flow, sort_keys=True)
        ))
        conn.execute("INSERT OR REPLACE INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
            f"card.flow.{flow_id}", "flow", flow_id, flow_id, body, flow.get("confidence"), int(bool(flow.get("needs_review", False))), json.dumps({"flow": flow}, sort_keys=True)
        ))

    for gap in gaps:
        gap_id = str(gap.get("id") or f"capability_gap.{gap.get('import_root')}")
        body = " ".join([str(gap.get("import_root", "")), str(gap.get("risk", "")), " ".join(gap.get("example_imports", [])), " ".join(gap.get("example_files", []))])
        conn.execute("INSERT OR REPLACE INTO capability_gaps VALUES (?, ?, ?, ?, ?, ?, ?)", (
            gap_id, gap.get("import_root"), gap.get("risk"), int(gap.get("file_count") or 0), int(gap.get("import_count") or 0), body, json.dumps(gap, sort_keys=True)
        ))
        conn.execute("INSERT OR REPLACE INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
            f"card.capability.{gap_id}", "capability_gap", gap_id, f"Unsupported import binding: {gap.get('import_root')}", body, gap.get("confidence"), 1, json.dumps({"capability_gap": gap}, sort_keys=True)
        ))

    fts = False
    try:
        conn.execute("CREATE VIRTUAL TABLE cards_fts USING fts5(id UNINDEXED, title, body)")
        conn.execute("INSERT INTO cards_fts(id, title, body) SELECT id, title, body FROM cards")
        fts = True
    except sqlite3.DatabaseError:
        fts = False

    counts = {
        "nodes": conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0],
        "edges": conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0],
        "facts": conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0],
        "flows": conn.execute("SELECT COUNT(*) FROM flows").fetchone()[0],
        "capability_gaps": conn.execute("SELECT COUNT(*) FROM capability_gaps").fetchone()[0],
        "cards": conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0],
    }
    conn.commit()
    conn.close()

    report = {
        "generated_at": generated,
        "status": "ok",
        "mcp_required": False,
        "database": str(DB),
        "source_of_truth": "atlas JSON/YAML artifacts",
        "fts_enabled": fts,
        "counts": counts,
        "usage": {
            "search": "python3 atlas/tools/codeatlas_context_pack.py search \"claims endpoint\"",
            "context_pack": "python3 atlas/tools/codeatlas_context_pack.py build \"why does claims search ignore archived records?\"",
            "trace": "python3 atlas/tools/codeatlas_context_pack.py trace \"POST /claims\"",
            "impact": "python3 atlas/tools/codeatlas_context_pack.py impact backend/app/routes/claims.py"
        }
    }
    write(ATLAS / "knowledge" / "sqlite-compile-report.json", report)
    print("read-model", report["database"], f"nodes={counts['nodes']}", f"edges={counts['edges']}", f"cards={counts['cards']}", f"fts={fts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
