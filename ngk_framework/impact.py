from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

from .base import Workspace, as_list, compact_json
from .drift import run_git
from .store import AtlasStore

def all_git_changed_files(ws: Workspace) -> set[str]:
    """Return paths changed in git diff/status, degrading to an empty set outside git."""
    files: set[str] = set()
    for args in (["diff", "--name-only", "HEAD", "--", "."], ["diff", "--name-only", "--cached", "--", "."]):
        code, out = run_git(ws, args)
        if code == 0 and out:
            files.update(line.strip() for line in out.splitlines() if line.strip())
    code, out = run_git(ws, ["status", "--porcelain=v1", "-z", "--", "."])
    if code != 0 or not out:
        return files
    parts = out.split("\0")
    i = 0
    while i < len(parts):
        entry = parts[i]
        i += 1
        if not entry:
            continue
        status = entry[:2]
        path = entry[2:].lstrip() if len(entry) > 2 else ""
        if status.startswith("R") or status.startswith("C"):
            if i < len(parts) and parts[i]:
                path = parts[i]
                i += 1
        if path:
            files.add(path)
    return files


def path_variants(path: str) -> set[str]:
    normalized = path.replace(os.sep, "/").lstrip("./")
    variants = {normalized}
    parts = normalized.split("/")
    for idx in range(1, len(parts)):
        variants.add("/".join(parts[idx:]))
    return {v for v in variants if v}


def paths_match(left: str, right: str) -> bool:
    if not left or not right:
        return False
    left_variants = path_variants(left)
    right_variants = path_variants(right)
    return bool(left_variants & right_variants) or any(a.endswith("/" + b) or b.endswith("/" + a) for a in left_variants for b in right_variants)


def confidence_for_edge(edge: dict[str, Any]) -> str:
    edge_type = str(edge.get("type") or "").lower().replace("_", "-")
    declared = str(edge.get("confidence") or "").lower()
    high_tokens = ("import", "symbol", "route", "hook", "api-client", "api.client", "calls-api")
    medium_tokens = ("field", "prop-chain", "prop", "property")
    low_tokens = ("dynamic", "runtime", "reflect")
    if any(token in edge_type for token in low_tokens) or declared == "low":
        return "low"
    if any(token in edge_type for token in medium_tokens) or declared == "medium":
        return "medium"
    if any(token in edge_type for token in high_tokens):
        return "high"
    return "high" if declared == "high" and not edge_type else "low"


def merge_confidence(current: str, new: str) -> str:
    order = {"low": 0, "medium": 1, "high": 2}
    return new if order.get(new, 0) > order.get(current, 0) else current


def row_raw(row: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(row.get("raw_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def all_facts(store: AtlasStore) -> list[dict[str, Any]]:
    with store.connect() as conn:
        return [dict(row) for row in conn.execute("select * from facts").fetchall()]


def all_evidence(store: AtlasStore) -> list[dict[str, Any]]:
    with store.connect() as conn:
        return [dict(row) for row in conn.execute("select * from evidence").fetchall()]


def all_source_spans(store: AtlasStore) -> list[dict[str, Any]]:
    with store.connect() as conn:
        return [dict(row) for row in conn.execute("select * from source_spans").fetchall()]


def add_impact_item(bucket: dict[str, dict[str, Any]], key: str, item: dict[str, Any], reason: str, confidence: str) -> None:
    if not key:
        return
    existing = bucket.setdefault(key, {**item, "reasons": [], "confidence": confidence})
    if reason and reason not in existing["reasons"]:
        existing["reasons"].append(reason)
    existing["confidence"] = merge_confidence(str(existing.get("confidence") or "low"), confidence)


def scan_nearby_tests(ws: Workspace, impacted_files: Iterable[str]) -> list[dict[str, str]]:
    tests: list[dict[str, str]] = []
    seen: set[str] = set()
    for impacted in impacted_files:
        variants = path_variants(impacted)
        base_names = {Path(v).stem for v in variants if v}
        dirs = {str(Path(v).parent).replace(".", "") for v in variants if str(Path(v).parent) != "."}
        for pattern in ("*test*", "*spec*"):
            for path in ws.source_root.rglob(pattern):
                if not path.is_file():
                    continue
                rel = path.relative_to(ws.source_root).as_posix()
                lower = rel.lower()
                if not any(token in lower for token in ("test", "spec")):
                    continue
                stem = path.stem.lower().replace(".test", "").replace(".spec", "")
                near_name = any(name.lower() and (name.lower() in stem or stem in name.lower()) for name in base_names)
                near_dir = any(directory and (rel.startswith(directory.rstrip("/") + "/") or directory.rstrip("/") in rel) for directory in dirs)
                if (near_name or near_dir) and rel not in seen:
                    seen.add(rel)
                    tests.append({"test_id": rel, "path": rel, "matched_file": impacted, "reason": f"near affected file {impacted} by naming/path convention"})
    return sorted(tests, key=lambda row: row["test_id"])



def scan_tests_importing_symbols(ws: Workspace, symbols: Iterable[str]) -> list[dict[str, str]]:
    wanted = {symbol for symbol in symbols if symbol}
    if not wanted:
        return []
    tests: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for pattern in ("*test*", "*spec*"):
        for path in ws.source_root.rglob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(ws.source_root).as_posix()
            lower = rel.lower()
            if not any(token in lower for token in ("test", "spec")):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for symbol in wanted:
                if re.search(r"\b" + re.escape(symbol) + r"\b", text):
                    key = (rel, symbol)
                    if key not in seen:
                        seen.add(key)
                        tests.append({"test_id": rel, "path": rel, "symbol": symbol, "reason": f"imports impacted symbol {symbol}"})
    return sorted(tests, key=lambda row: (row["test_id"], row["symbol"]))

def compute_impact(ws: Workspace, *, target: str | None = None, changed: bool = False, max_depth: int = 2) -> dict[str, Any]:
    store = AtlasStore(ws)
    store.connect().close()
    facts_by_id = {fact["fact_id"]: fact for fact in all_facts(store)}
    evidence = all_evidence(store)
    spans = all_source_spans(store)
    nodes = store.graph_nodes()
    edges = store.graph_edges()
    traces = store.traces()

    impacted_files: dict[str, dict[str, Any]] = {}
    impacted_spans: dict[str, dict[str, Any]] = {}
    impacted_nodes: dict[str, dict[str, Any]] = {}
    impacted_facts: dict[str, dict[str, Any]] = {}
    impacted_traces: dict[str, dict[str, Any]] = {}

    changed_files = sorted(all_git_changed_files(ws)) if changed else []
    for path in changed_files:
        add_impact_item(impacted_files, path, {"path": path}, "changed in git diff/status", "high")

    if target:
        target_path = target.replace(os.sep, "/")
        if any(paths_match(target_path, row.get("path", "")) for row in [*evidence, *spans, *nodes]) or "/" in target_path or "." in Path(target_path).name:
            add_impact_item(impacted_files, target_path, {"path": target_path}, "requested target", "high")
        fact = store.get_fact(target)
        if fact:
            add_impact_item(impacted_facts, fact["fact_id"], dict(fact), "requested fact target", "high")
        trace_report = store.trace_report(target)
        trace = trace_report.get("trace")
        if trace:
            add_impact_item(impacted_traces, trace["trace_id"], trace, "requested trace target", str(trace.get("confidence") or "high"))
        resolved = store.resolve_graph_target(target)
        if resolved.get("match_type") != "literal" or target in {node.get("node_id") for node in nodes}:
            node_id = resolved.get("node_id") or ""
            node = resolved.get("node") or next((n for n in nodes if n.get("node_id") == node_id), {})
            add_impact_item(impacted_nodes, node_id, {"node_id": node_id, "node": node}, f"requested graph target ({resolved.get('match_type')})", "high")

    changed_inputs = list(impacted_files)
    for path in changed_inputs:
        for span in spans:
            if paths_match(path, span.get("path", "")):
                add_impact_item(impacted_spans, span["span_id"], span, f"source span in affected file {path}", "high")
        for ev in evidence:
            if paths_match(path, ev.get("path", "")):
                fact = facts_by_id.get(ev["fact_id"], {"fact_id": ev["fact_id"]})
                add_impact_item(impacted_facts, ev["fact_id"], fact, f"evidence path {ev.get('path')} is affected", "high")
                if ev.get("span_id"):
                    span = next((s for s in spans if s.get("span_id") == ev.get("span_id")), {"span_id": ev.get("span_id"), "path": ev.get("path")})
                    add_impact_item(impacted_spans, ev["span_id"], span, f"evidence span for affected file {path}", "high")
        for node in nodes:
            if paths_match(path, node.get("path", "")):
                add_impact_item(impacted_nodes, node["node_id"], {"node_id": node["node_id"], "node": node}, f"graph node path {node.get('path')} is affected", "high")

    for ev in evidence:
        if ev.get("span_id") in impacted_spans:
            fact = facts_by_id.get(ev["fact_id"], {"fact_id": ev["fact_id"]})
            add_impact_item(impacted_facts, ev["fact_id"], fact, f"fact uses impacted source span {ev.get('span_id')}", "high")

    for node in nodes:
        raw = row_raw(node)
        if node.get("node_id") in impacted_spans or any(fid in impacted_facts for fid in as_list(raw.get("fact_ids"))):
            add_impact_item(impacted_nodes, node["node_id"], {"node_id": node["node_id"], "node": node}, "node is linked to impacted span/fact", "high")

    frontier = set(impacted_nodes)
    visited = set(frontier)
    for _depth in range(max_depth):
        next_frontier: set[str] = set()
        for edge in edges:
            from_id = edge.get("from_id") or ""
            to_id = edge.get("to_id") or ""
            if from_id in frontier or to_id in frontier:
                neighbor = to_id if from_id in frontier else from_id
                if not neighbor:
                    continue
                confidence = confidence_for_edge(edge)
                node = next((n for n in nodes if n.get("node_id") == neighbor), {})
                add_impact_item(impacted_nodes, neighbor, {"node_id": neighbor, "node": node}, f"graph edge {edge.get('edge_id')} ({edge.get('type') or 'unknown'}) from impacted node", confidence)
                for fact_id in as_list(row_raw(edge).get("fact_ids")):
                    if fact_id in facts_by_id:
                        add_impact_item(impacted_facts, str(fact_id), facts_by_id[str(fact_id)], f"graph edge {edge.get('edge_id')} links fact", confidence)
                if neighbor not in visited:
                    next_frontier.add(neighbor)
                    visited.add(neighbor)
        frontier = next_frontier

    impacted_blob = compact_json({"facts": list(impacted_facts), "spans": list(impacted_spans), "nodes": list(impacted_nodes)})
    for trace in traces:
        raw = row_raw(trace)
        blob = compact_json(raw)
        explicit_fact_ids = {str(x) for x in as_list(raw.get("fact_ids"))}
        if any(key and key in blob for key in [*impacted_spans, *impacted_nodes]) or explicit_fact_ids & set(impacted_facts) or any(fid and fid in impacted_blob for fid in explicit_fact_ids):
            add_impact_item(impacted_traces, trace["trace_id"], trace, "trace references impacted fact/span/node", str(trace.get("confidence") or raw.get("confidence") or "medium"))
            for fact in store.facts_for_trace(trace):
                add_impact_item(impacted_facts, fact["fact_id"], fact, f"fact is related to impacted trace {trace['trace_id']}", str(trace.get("confidence") or "medium"))

    return {
        "target": target,
        "changed": changed,
        "changed_files": changed_files,
        "files": sorted(impacted_files.values(), key=lambda x: x["path"]),
        "source_spans": sorted(impacted_spans.values(), key=lambda x: x.get("span_id", "")),
        "nodes": sorted(impacted_nodes.values(), key=lambda x: x.get("node_id", "")),
        "facts": sorted(impacted_facts.values(), key=lambda x: x.get("fact_id", "")),
        "traces": sorted(impacted_traces.values(), key=lambda x: x.get("trace_id", "")),
    }


def select_tests_from_impact(ws: Workspace, impact: dict[str, Any]) -> dict[str, Any]:
    store = AtlasStore(ws)
    selected: dict[str, dict[str, Any]] = {}

    def add_test(test_id: str, reason: str, *, confidence: str = "high", path: str = "") -> None:
        if not test_id:
            return
        entry = selected.setdefault(test_id, {"test_id": test_id, "path": path or test_id, "reasons": [], "confidence": confidence})
        if reason not in entry["reasons"]:
            entry["reasons"].append(reason)
        entry["confidence"] = merge_confidence(entry.get("confidence", "low"), confidence)

    impacted_fact_ids = [fact.get("fact_id") for fact in impact.get("facts", []) if fact.get("fact_id")]
    impacted_node_ids = [node.get("node_id") for node in impact.get("nodes", []) if node.get("node_id")]
    impacted_files = [item.get("path") for item in impact.get("files", []) if item.get("path")]

    for fact_id in impacted_fact_ids:
        for test in store.related_tests(fact_id):
            add_test(test, f"directly covers fact {fact_id}", confidence="high")

    for trace in impact.get("traces", []):
        raw = row_raw(trace)
        for test in as_list(raw.get("related_tests") or raw.get("tests")):
            add_test(str(test), f"linked through trace {trace.get('trace_id')}", confidence=str(trace.get("confidence") or "high"))

    nodes_by_id = {node["node_id"]: node for node in store.graph_nodes()}
    for edge in store.graph_edges():
        raw = row_raw(edge)
        endpoints = [edge.get("from_id") or "", edge.get("to_id") or ""]
        fact_ids = {str(x) for x in as_list(raw.get("fact_ids"))}
        touches_impact = bool(set(endpoints) & set(impacted_node_ids) or fact_ids & set(impacted_fact_ids))
        if not touches_impact:
            continue
        confidence = confidence_for_edge(edge)
        for endpoint in endpoints:
            node = nodes_by_id.get(endpoint, {})
            node_raw = row_raw(node) if node else {}
            is_test = "test" in endpoint.lower() or "test" in str(node.get("kind", "")).lower() or "test" in str(node.get("path", "")).lower()
            if is_test:
                add_test(endpoint, f"linked through graph/test edge {edge.get('edge_id')}", confidence=confidence, path=str(node.get("path") or endpoint))
            for test in as_list(node_raw.get("tests") or node_raw.get("related_tests")):
                add_test(str(test), f"linked through graph node {endpoint}", confidence=confidence)

    for item in impact.get("nodes", []):
        node = item.get("node") or {}
        symbol = str(node.get("symbol") or node.get("label") or item.get("node_id") or "")
        path = str(node.get("path") or "")
        if not symbol:
            continue
        for test in scan_tests_importing_symbols(ws, [symbol]):
            add_test(test["test_id"], test["reason"], confidence="high", path=test.get("path", ""))
        for test in scan_nearby_tests(ws, [path] if path else []):
            add_test(test["test_id"], test["reason"], confidence="medium", path=test.get("path", ""))

    for test in scan_nearby_tests(ws, impacted_files):
        add_test(test["test_id"], test["reason"], confidence="medium", path=test.get("path", ""))

    covered_facts = {fact_id: bool(store.related_tests(fact_id)) for fact_id in impacted_fact_ids}
    covered_traces: dict[str, bool] = {}
    for trace in impact.get("traces", []):
        raw = row_raw(trace)
        tests = as_list(raw.get("related_tests") or raw.get("tests"))
        covered_traces[str(trace.get("trace_id"))] = bool(tests)
    coverage_gaps = {
        "facts": sorted(fact_id for fact_id, covered in covered_facts.items() if not covered),
        "traces": sorted(trace_id for trace_id, covered in covered_traces.items() if trace_id and not covered),
    }
    return {
        "impact": impact,
        "selected_tests": sorted(selected.values(), key=lambda item: item["test_id"]),
        "coverage_gaps": coverage_gaps,
    }


