#!/usr/bin/env python3
"""Build no-MCP CodeAtlas context packs from local artifacts/read model.

In strict mode this tool validates artifacts before writing any context pack. A
context pack is a derived AI-facing view, so it must fail closed when canonical
artifacts are invalid.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
ATLAS = ROOT / "atlas"
DB = ATLAS / "knowledge" / "atlas.sqlite"
VALIDATOR = ATLAS / "tools" / "validate_artifacts.py"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_strict_validation() -> int:
    if not VALIDATOR.exists():
        print(f"missing validator: {VALIDATOR}", file=sys.stderr)
        return 1
    return subprocess.run([sys.executable, str(VALIDATOR), str(ATLAS), "--strict"], cwd=ROOT).returncode


def require_valid_if_strict(args: argparse.Namespace) -> int:
    if getattr(args, "strict", False):
        code = run_strict_validation()
        if code:
            print("strict validation failed; refusing to emit CodeAtlas context output", file=sys.stderr)
        return code
    return 0


def slug(value: object) -> str:
    text = re.sub(r"[^A-Za-z0-9_./:@-]+", "_", str(value).replace("\\", "/").strip("/"))
    return re.sub(r"\.+", ".", text.replace("/", ".").replace(":", ".").replace("-", "_")).strip(".")[:120] or "context"


def read(path: Path, default: Any) -> Any:
    paths = [path, path.with_suffix(".yaml")] if path.suffix == ".json" else [path.with_suffix(".json"), path] if path.suffix == ".yaml" else [path]
    for p in paths:
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "data" in data and "artifact_kind" in data:
                    return data.get("data") or default
                return data
            except Exception:
                return default
    return default


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def terms(text: str) -> list[str]:
    return [x.lower() for x in re.split(r"[^A-Za-z0-9_/@.-]+", text) if len(x) > 1]


def score(text: str, query: str) -> int:
    low = text.lower()
    return sum(3 if t in low else 0 for t in terms(query))


def graph() -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    nodes = read(ATLAS / "graph" / "nodes.json", {}).get("nodes", [])
    edges = read(ATLAS / "graph" / "edges.json", {}).get("edges", [])
    if not nodes:
        data = read(ATLAS / "visualizer" / "graph-data.json", {})
        nodes = data.get("nodes", [])
        edges = data.get("edges", edges)
    return {str(n.get("id")): n for n in nodes if n.get("id")}, edges


def facts() -> list[dict[str, Any]]:
    return read(ATLAS / "facts" / "technical-facts.json", {}).get("technical_facts", [])


def flows() -> list[dict[str, Any]]:
    result = []
    result += read(ATLAS / "flows" / "api-request-flows.json", {}).get("api_request_flows", [])
    result += read(ATLAS / "flows" / "ui-flows.json", {}).get("ui_flows", [])
    result += read(ATLAS / "errors" / "error-flow-index.json", {}).get("error_flows", [])
    return result


def gaps() -> list[dict[str, Any]]:
    return read(ATLAS / "audit" / "capability-gaps.json", {}).get("capability_gaps", [])


def search_cards(query: str, limit: int) -> list[dict[str, Any]]:
    if not DB.exists():
        return []
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        try:
            rows = conn.execute(
                "SELECT c.* FROM cards_fts JOIN cards c ON c.id = cards_fts.id WHERE cards_fts MATCH ? LIMIT ?",
                (" ".join(terms(query)) or query, limit),
            ).fetchall()
            if rows:
                return [dict(r) for r in rows]
        except sqlite3.DatabaseError:
            pass
        like = f"%{query}%"
        rows = conn.execute("SELECT * FROM cards WHERE lower(title) LIKE lower(?) OR lower(body) LIKE lower(?) LIMIT ?", (like, like, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def ids_from_cards(cards: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for c in cards:
        if c.get("node_id") and str(c["node_id"]) not in ids:
            ids.append(str(c["node_id"]))
        try:
            raw = json.loads(str(c.get("json", "{}")))
        except Exception:
            raw = {}
        for item in raw.values() if isinstance(raw, dict) else []:
            if isinstance(item, dict):
                for key in ("id", "source_id", "source", "endpoint"):
                    value = item.get(key)
                    if value and str(value) not in ids:
                        ids.append(str(value))
    return ids


def artifact_search(query: str, limit: int) -> list[str]:
    node_by_id, _ = graph()
    scored = []
    for node in node_by_id.values():
        text = " ".join(str(node.get(k, "")) for k in ("id", "type", "repo", "file", "name", "path", "function"))
        s = score(text, query)
        if s:
            scored.append((s, str(node.get("id"))))
    return [node_id for _, node_id in sorted(scored, key=lambda x: (-x[0], x[1]))[:limit]]


def sqlite_selection(ids: list[str], limit: int) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    if not DB.exists() or not ids:
        return {}, []
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        for node_id in ids[:limit]:
            row = conn.execute("SELECT json FROM nodes WHERE id = ?", (node_id,)).fetchone()
            if row:
                node = json.loads(row["json"])
                nodes[str(node.get("id"))] = node
        if ids:
            ph = ",".join("?" for _ in ids[:limit])
            rows = conn.execute(f"SELECT json FROM edges WHERE source IN ({ph}) OR target IN ({ph}) LIMIT ?", [*ids[:limit], *ids[:limit], limit * 5]).fetchall()
            for row in rows:
                edge = json.loads(row["json"])
                edges.append(edge)
                for endpoint in (edge.get("source"), edge.get("target")):
                    if endpoint and endpoint not in nodes:
                        nrow = conn.execute("SELECT json FROM nodes WHERE id = ?", (endpoint,)).fetchone()
                        if nrow:
                            node = json.loads(nrow["json"])
                            nodes[str(node.get("id"))] = node
        return nodes, edges
    finally:
        conn.close()


def trace_edges(start: str, direction: str, depth: int, limit: int) -> list[dict[str, Any]]:
    _, edges = graph()
    result: list[dict[str, Any]] = []
    queue = deque([(start, 0)])
    seen = {start}
    while queue and len(result) < limit:
        current, d = queue.popleft()
        if d >= depth:
            continue
        for edge in edges:
            source = str(edge.get("source"))
            target = str(edge.get("target"))
            match = (direction in {"out", "both"} and source == current) or (direction in {"in", "both"} and target == current)
            if not match:
                continue
            result.append(edge)
            nxt = target if source == current else source
            if nxt and nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, d + 1))
    return result[:limit]


def build(query: str, mode: str, limit: int, depth: int, direction: str = "both") -> dict[str, Any]:
    cards = search_cards(query, limit)
    ids = ids_from_cards(cards) or artifact_search(query, limit)
    selected_nodes, selected_edges = sqlite_selection(ids, limit)
    if not selected_nodes:
        selected_nodes, all_edges = graph()
        selected_nodes = {k: v for k, v in selected_nodes.items() if k in ids[:limit]}
        selected_edges = [e for e in all_edges if str(e.get("source")) in selected_nodes or str(e.get("target")) in selected_nodes][: limit * 5]
    if mode == "trace":
        traced = []
        for node_id in ids[:5]:
            traced += trace_edges(node_id, direction, depth, limit * 3)
        selected_edges = traced or selected_edges
    fs = facts()
    fl = flows()
    capability_gaps = gaps()
    pack_id = f"{mode}.{slug(query)}"
    return {
        "id": pack_id,
        "schema_version": "codeatlas.context-pack.v1",
        "generated_at": now(),
        "mode": mode,
        "query": query,
        "mcp_required": False,
        "selected_cards": cards,
        "selected_nodes": list(selected_nodes.values()),
        "selected_edges": selected_edges,
        "related_facts": fs[:limit],
        "related_flows": fl[:limit],
        "capability_gaps": capability_gaps[:limit],
        "selection_summary": {
            "cards": len(cards),
            "nodes": len(selected_nodes),
            "edges": len(selected_edges),
            "facts": min(len(fs), limit),
            "flows": min(len(fl), limit),
            "capability_gaps": min(len(capability_gaps), limit),
        },
        "llm_instructions": [
            "Treat this pack as derived context, not source code authority.",
            "Cite evidence IDs/paths from selected nodes, edges, facts, and flows when making claims.",
            "Do not infer behaviour for unsupported capability gaps.",
            "If the pack lacks evidence for a claim, say the claim is unknown or needs review.",
        ],
    }


def write_markdown(pack: dict[str, Any], path: Path) -> None:
    lines = [f"# CodeAtlas context pack: {pack['query']}", "", f"Mode: `{pack['mode']}`", f"Generated: `{pack['generated_at']}`", "", "## Selection summary", ""]
    for key, value in pack["selection_summary"].items():
        lines.append(f"- {key}: {value}")
    lines.append("\n## Nodes")
    for node in pack["selected_nodes"][:30]:
        lines.append(f"- `{node.get('id')}` {node.get('type')} {node.get('file') or node.get('path') or ''}")
    lines.append("\n## Edges")
    for edge in pack["selected_edges"][:50]:
        lines.append(f"- `{edge.get('source')}` -[{edge.get('type')}]-> `{edge.get('target')}` confidence={edge.get('confidence')}")
    lines.append("\n## Facts")
    for fact in pack["related_facts"][:30]:
        lines.append(f"- `{fact.get('id')}` {fact.get('statement')}")
    lines.append("\n## Capability gaps")
    for w in pack["capability_gaps"][:30]:
        lines.append(f"- `{w.get('import_root')}` risk={w.get('risk')}")
    lines.append("\n## LLM instructions")
    lines += [f"- {x}" for x in pack["llm_instructions"]]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def emit(args: argparse.Namespace, mode: str) -> int:
    validation_code = require_valid_if_strict(args)
    if validation_code:
        return validation_code
    pack = build(args.query, mode, args.limit, args.depth, getattr(args, "direction", "both"))
    out = ATLAS / "context-packs"
    json_path = out / f"{pack['id']}.json"
    md_path = out / f"{pack['id']}.md"
    write(json_path, pack)
    write_markdown(pack, md_path)
    if args.json:
        print(json.dumps(pack, indent=2, sort_keys=True))
    else:
        print(f"wrote {json_path}")
        print(f"wrote {md_path}")
        print(json.dumps(pack["selection_summary"], indent=2, sort_keys=True))
    return 0 if pack["selected_nodes"] or pack["selected_edges"] or pack["selected_cards"] else 1


def search(args: argparse.Namespace) -> int:
    validation_code = require_valid_if_strict(args)
    if validation_code:
        return validation_code
    matches = search_cards(args.query, args.limit) if DB.exists() else [{"id": x} for x in artifact_search(args.query, args.limit)]
    print(json.dumps({"query": args.query, "matches": matches}, indent=2, sort_keys=True) if args.json else "\n".join(str(m.get("id")) for m in matches))
    return 0 if matches else 1


def ready(args: argparse.Namespace) -> int:
    validation_code = require_valid_if_strict(args)
    payload = {
        "status": "ok" if validation_code == 0 else "error",
        "strict": bool(getattr(args, "strict", False)),
        "database_exists": DB.exists(),
        "context_pack_dir": str(ATLAS / "context-packs"),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return validation_code


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Validate artifacts before reading/writing context output")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build no-MCP CodeAtlas context packs.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    ready_parser = sub.add_parser("ready")
    ready_parser.add_argument("--strict", action="store_true", help="Validate artifacts and report context-pack readiness")
    ready_parser.set_defaults(func=ready)
    for name in ["search", "build", "trace", "impact"]:
        p = sub.add_parser(name)
        p.add_argument("query")
        add_common_args(p)
        if name == "trace":
            p.add_argument("--direction", choices=["in", "out", "both"], default="both")
        p.set_defaults(func=search if name == "search" else (lambda args, mode=name: emit(args, mode)))
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
