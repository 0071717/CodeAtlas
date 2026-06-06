#!/usr/bin/env python3
"""Build no-MCP CodeAtlas context packs from local artifacts/read model."""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
ATLAS = ROOT / "atlas"
DB = ATLAS / "knowledge" / "atlas.sqlite"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: object) -> str:
    text = re.sub(r"[^A-Za-z0-9_./:@-]+", "_", str(value).replace("\\", "/").strip("/"))
    return re.sub(r"\.+", ".", text.replace("/", ".").replace(":", ".").replace("-", "_")).strip(".")[:120] or "context"


def read(path: Path, default: Any) -> Any:
    paths = [path, path.with_suffix(".yaml")] if path.suffix == ".json" else [path.with_suffix(".json"), path] if path.suffix == ".yaml" else [path]
    for p in paths:
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
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
    node_by_id, all_edges = graph()
    by_source: dict[str, list[dict[str, Any]]] = {}
    by_target: dict[str, list[dict[str, Any]]] = {}
    for e in all_edges:
        by_source.setdefault(str(e.get("source")), []).append(e)
        by_target.setdefault(str(e.get("target")), []).append(e)
    out: list[dict[str, Any]] = []
    seen = {start}
    queue = deque([(start, 0)])
    while queue and len(out) < limit:
        node, dist = queue.popleft()
        if dist >= depth:
            continue
        candidates = []
        if direction in {"out", "both"}:
            candidates += by_source.get(node, [])
        if direction in {"in", "both"}:
            candidates += by_target.get(node, [])
        for edge in candidates:
            out.append(edge)
            nxt = edge.get("target") if edge.get("source") == node else edge.get("source")
            if nxt and str(nxt) not in seen and str(nxt) in node_by_id:
                seen.add(str(nxt))
                queue.append((str(nxt), dist + 1))
            if len(out) >= limit:
                break
    return out


def evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for item in items:
        evs = list(item.get("evidence", [])) if isinstance(item, dict) else []
        if isinstance(item, dict) and item.get("file"):
            evs.append({"type": "code", "repo": item.get("repo"), "file": item.get("file")})
        for ev in evs:
            key = (ev.get("repo"), ev.get("file"), ev.get("line_start"), ev.get("line_end")) if isinstance(ev, dict) else None
            if key and ev.get("file") and key not in seen:
                seen.add(key)
                result.append(ev)
    return result


def warnings_for(nodes: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    selected_files = {f"{n.get('repo')}:{n.get('file')}" for n in nodes if n.get("file")}
    q = query.lower()
    matched = []
    for gap in gaps():
        root = str(gap.get("import_root", "")).lower()
        if root in q or selected_files & set(gap.get("example_files", [])):
            matched.append(gap)
    return (matched or gaps()[:3])[:8]


def build(query: str, mode: str, limit: int, depth: int, direction: str) -> dict[str, Any]:
    cards = search_cards(query, limit)
    ids = ids_from_cards(cards) or artifact_search(query, limit)
    node_by_id, all_edges = graph()
    selected_nodes, selected_edges = sqlite_selection(ids, limit)

    if not selected_nodes:
        for node_id in ids[:limit]:
            if node_id in node_by_id:
                selected_nodes[node_id] = node_by_id[node_id]
        chosen = set(selected_nodes)
        selected_edges = [e for e in all_edges if e.get("source") in chosen or e.get("target") in chosen][:limit * 5]
        for e in selected_edges:
            for endpoint in (e.get("source"), e.get("target")):
                if endpoint in node_by_id:
                    selected_nodes[str(endpoint)] = node_by_id[str(endpoint)]

    if mode == "trace" and ids:
        for e in trace_edges(ids[0], direction, depth, limit * 5):
            selected_edges.append(e)
            for endpoint in (e.get("source"), e.get("target")):
                if endpoint in node_by_id:
                    selected_nodes[str(endpoint)] = node_by_id[str(endpoint)]

    if mode == "impact":
        q = query.lower()
        for node in node_by_id.values():
            if q in str(node.get("file", "")).lower():
                selected_nodes[str(node.get("id"))] = node
        chosen = set(selected_nodes)
        selected_edges += [e for e in all_edges if e.get("source") in chosen or e.get("target") in chosen][:limit * 5]

    node_list = sorted(selected_nodes.values(), key=lambda n: str(n.get("id")))[:limit * 3]
    edge_list = sorted({str(e.get("id")): e for e in selected_edges}.values(), key=lambda e: str(e.get("id")))[:limit * 5]
    fact_list = [f for f in facts() if f.get("source_id") in selected_nodes or f.get("id") in selected_nodes][:limit]
    flow_list = [f for f in flows() if any(nid in json.dumps(f) for nid in list(selected_nodes)[:10])][:limit]
    warn = warnings_for(node_list, query)

    return {
        "id": f"{mode}.{slug(query)}",
        "generated_at": now(),
        "query": query,
        "mode": mode,
        "mcp_required": False,
        "read_model": {"used": DB.exists(), "path": str(DB) if DB.exists() else None},
        "selection_summary": {
            "matched_card_count": len(cards),
            "selected_node_count": len(node_list),
            "selected_edge_count": len(edge_list),
            "selected_fact_count": len(fact_list),
            "selected_flow_count": len(flow_list),
            "capability_warning_count": len(warn)
        },
        "selected_cards": [{"id": c.get("id"), "kind": c.get("kind"), "node_id": c.get("node_id"), "title": c.get("title"), "body": c.get("body")} for c in cards[:limit]],
        "selected_nodes": node_list,
        "selected_edges": edge_list,
        "selected_facts": fact_list,
        "selected_flows": flow_list,
        "evidence": evidence(node_list + edge_list + fact_list + flow_list),
        "capability_warnings": warn,
        "known_unknowns": [{"type": "unsupported_library_binding", "import_root": w.get("import_root"), "risk": w.get("risk")} for w in warn],
        "llm_instructions": [
            "Use this context pack before reading broad source files.",
            "Do not infer semantics for unsupported libraries listed in capability_warnings.",
            "If source code and Atlas disagree, source code wins.",
            "Cite repo/file/line evidence when answering."
        ],
    }


def write_markdown(pack: dict[str, Any], path: Path) -> None:
    lines = [f"# CodeAtlas context pack: {pack['query']}", "", f"- mode: `{pack['mode']}`", f"- mcp_required: `{pack['mcp_required']}`", ""]
    lines.append("## Selection summary")
    for k, v in pack["selection_summary"].items():
        lines.append(f"- {k}: {v}")
    lines.append("\n## Selected nodes")
    for n in pack["selected_nodes"][:30]:
        lines.append(f"- `{n.get('id')}` ({n.get('type')}) — {n.get('repo')}:{n.get('file')}")
    lines.append("\n## Selected edges")
    for e in pack["selected_edges"][:50]:
        lines.append(f"- `{e.get('source')}` --{e.get('type')}--> `{e.get('target')}`")
    if pack["capability_warnings"]:
        lines.append("\n## Capability warnings")
        for w in pack["capability_warnings"]:
            lines.append(f"- `{w.get('import_root')}` risk={w.get('risk')}")
    lines.append("\n## LLM instructions")
    lines += [f"- {x}" for x in pack["llm_instructions"]]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def emit(args: argparse.Namespace, mode: str) -> int:
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
    matches = search_cards(args.query, args.limit) if DB.exists() else [{"id": x} for x in artifact_search(args.query, args.limit)]
    print(json.dumps({"query": args.query, "matches": matches}, indent=2, sort_keys=True) if args.json else "\n".join(str(m.get("id")) for m in matches))
    return 0 if matches else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Build no-MCP CodeAtlas context packs.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ["search", "build", "trace", "impact"]:
        p = sub.add_parser(name)
        p.add_argument("query")
        p.add_argument("--limit", type=int, default=20)
        p.add_argument("--depth", type=int, default=3)
        p.add_argument("--json", action="store_true")
        if name == "trace":
            p.add_argument("--direction", choices=["in", "out", "both"], default="both")
        p.set_defaults(func=search if name == "search" else (lambda args, mode=name: emit(args, mode)))
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
