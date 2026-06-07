from __future__ import annotations

import json
import sqlite3
from typing import Any

from .base import TOKEN_RE, Workspace, as_list, compact_json
from .indexer import AtlasIndexer

class AtlasStore:
    def __init__(self, ws: Workspace) -> None:
        self.ws = ws

    def connect(self) -> sqlite3.Connection:
        if not self.ws.db.exists():
            AtlasIndexer(self.ws).index()
        conn = sqlite3.connect(self.ws.db)
        conn.row_factory = sqlite3.Row
        return conn

    def score_text(self, query: str, text: str) -> int:
        terms = [t.lower() for t in TOKEN_RE.findall(query)]
        lower = text.lower()
        score = sum(1 for term in terms if term in lower)
        if query.lower() and query.lower() in lower:
            score += 5
        return score

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("select * from retrieval_items").fetchall()
        scored = []
        for row in rows:
            text = " ".join(str(row[k] or "") for k in row.keys())
            score = self.score_text(query, text)
            if score:
                scored.append((score + float(row["priority"] or 0), dict(row)))
        return [r for _, r in sorted(scored, key=lambda x: x[0], reverse=True)[:limit]]

    def search_facts(self, query: str, limit: int = 20) -> list[sqlite3.Row]:
        terms = [t.lower() for t in TOKEN_RE.findall(query)]
        with self.connect() as conn:
            rows = conn.execute("select * from facts").fetchall()
        scored = []
        for row in rows:
            text = " ".join(str(row[k] or "") for k in row.keys()).lower()
            score = sum(1 for term in terms if term in text)
            if query in row["fact_id"]:
                score += 10
            if score:
                scored.append((score, row))
        return [r for _, r in sorted(scored, key=lambda x: x[0], reverse=True)[:limit]]

    def get_fact(self, fact_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("select * from facts where fact_id=?", (fact_id,)).fetchone()

    def get_evidence(self, fact_id: str) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute("select * from evidence where fact_id=?", (fact_id,)).fetchall()

    def get_source_span(self, span_id: str) -> sqlite3.Row | None:
        if not span_id:
            return None
        with self.connect() as conn:
            return conn.execute("select * from source_spans where span_id=?", (span_id,)).fetchone()

    def related_traces(self, fact_id: str) -> list[dict[str, Any]]:
        fact = self.get_fact(fact_id)
        if not fact:
            return []
        raw = json.loads(fact["raw_json"] or "{}")
        explicit = set()
        related = raw.get("related") if isinstance(raw, dict) else {}
        if isinstance(related, dict):
            explicit.update(str(x) for x in as_list(related.get("traces")))
        span_ids = {ev["span_id"] for ev in self.get_evidence(fact_id) if ev["span_id"]}
        with self.connect() as conn:
            traces = conn.execute("select * from traces").fetchall()
        matches: list[dict[str, Any]] = []
        for trace in traces:
            raw_trace = json.loads(trace["raw_json"] or "{}")
            blob = compact_json(raw_trace)
            if trace["trace_id"] in explicit or fact_id in blob or any(span_id in blob for span_id in span_ids):
                matches.append(dict(trace))
        return matches

    def related_tests(self, fact_id: str) -> list[str]:
        fact = self.get_fact(fact_id)
        tests: set[str] = set()
        if fact:
            raw = json.loads(fact["raw_json"] or "{}")
            related = raw.get("related") if isinstance(raw, dict) else {}
            if isinstance(related, dict):
                tests.update(str(x) for x in as_list(related.get("tests")))
        for trace in self.related_traces(fact_id):
            raw_trace = json.loads(trace["raw_json"] or "{}")
            tests.update(str(x) for x in as_list(raw_trace.get("related_tests") or raw_trace.get("tests")))
        return sorted(tests)

    def graph_nodes(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute("select * from nodes").fetchall()]

    def graph_edges(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute("select * from edges").fetchall()]

    def traces(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            return [dict(row) for row in conn.execute("select * from traces").fetchall()]

    def resolve_graph_target(self, target: str) -> dict[str, Any]:
        target_lower = target.lower()
        nodes = self.graph_nodes()
        for node in nodes:
            values = [node.get("node_id", ""), node.get("symbol", ""), node.get("label", ""), node.get("path", "")]
            if any(target == str(value) for value in values if value):
                return {"target": target, "node_id": node["node_id"], "match_type": "node", "node": node}
        for node in nodes:
            values = [node.get("node_id", ""), node.get("symbol", ""), node.get("label", ""), node.get("path", "")]
            if any(target_lower in str(value).lower() for value in values if value):
                return {"target": target, "node_id": node["node_id"], "match_type": "node", "node": node}
        for edge in self.graph_edges():
            for key in ("from_id", "to_id"):
                endpoint = str(edge.get(key) or "")
                if target == endpoint or (target_lower and target_lower in endpoint.lower()):
                    return {"target": target, "node_id": endpoint, "match_type": "edge_endpoint", "node": {}}
        for row in self.search(target, limit=10):
            for key in ("symbol", "trace_id", "fact_id", "item_id"):
                value = str(row.get(key) or "")
                if value and (target == value or target_lower in value.lower()):
                    return {"target": target, "node_id": value, "match_type": f"retrieval_{key}", "node": {}}
        return {"target": target, "node_id": target, "match_type": "literal", "node": {}}

    def graph_neighbors(self, target: str, *, reverse: bool = False) -> dict[str, Any]:
        resolved = self.resolve_graph_target(target)
        node_id = resolved["node_id"]
        edges = self.graph_edges()
        key_from, key_to = ("to_id", "from_id") if reverse else ("from_id", "to_id")
        matches = [edge for edge in edges if edge.get(key_from) == node_id]
        neighbors = []
        nodes_by_id = {node["node_id"]: node for node in self.graph_nodes()}
        for edge in matches:
            neighbor_id = edge.get(key_to) or ""
            neighbors.append({"node_id": neighbor_id, "node": nodes_by_id.get(neighbor_id, {}), "edge": edge})
        return {"matched_target": resolved, "direction": "reverse" if reverse else "forward", "neighbors": neighbors}

    def graph_path(self, start: str, end: str, *, max_depth: int = 6) -> dict[str, Any]:
        start_resolved = self.resolve_graph_target(start)
        end_resolved = self.resolve_graph_target(end)
        start_id = start_resolved["node_id"]
        end_id = end_resolved["node_id"]
        edges = self.graph_edges()
        adjacency: dict[str, list[dict[str, Any]]] = {}
        for edge in edges:
            adjacency.setdefault(edge.get("from_id") or "", []).append(edge)
        queue: list[tuple[str, list[dict[str, Any]]]] = [(start_id, [])]
        visited = {start_id}
        found: list[dict[str, Any]] | None = [] if start_id == end_id else None
        while queue and found is None:
            node_id, path_edges = queue.pop(0)
            if len(path_edges) >= max_depth:
                continue
            for edge in sorted(adjacency.get(node_id, []), key=lambda item: (item.get("type") or "", item.get("to_id") or "", item.get("edge_id") or "")):
                next_id = edge.get("to_id") or ""
                if not next_id or next_id in visited:
                    continue
                new_path = [*path_edges, edge]
                if next_id == end_id:
                    found = new_path
                    break
                visited.add(next_id)
                queue.append((next_id, new_path))
        nodes_by_id = {node["node_id"]: node for node in self.graph_nodes()}
        node_path = [start_id]
        if found:
            node_path.extend(edge.get("to_id") or "" for edge in found)
        return {
            "from": start_resolved,
            "to": end_resolved,
            "found": found is not None,
            "max_depth": max_depth,
            "nodes": [{"node_id": node_id, "node": nodes_by_id.get(node_id, {})} for node_id in node_path] if found is not None else [],
            "edges": found or [],
        }

    def resolve_trace_target(self, target: str) -> dict[str, Any]:
        target_lower = target.lower()
        traces = self.traces()
        for trace in traces:
            raw = json.loads(trace["raw_json"] or "{}")
            values = [trace.get("trace_id", ""), trace.get("title", ""), trace.get("summary", ""), compact_json(raw)]
            if any(target == str(value) for value in values if value):
                return {"target": target, "match_type": "trace", "trace": trace}
        for trace in traces:
            raw = json.loads(trace["raw_json"] or "{}")
            values = [trace.get("trace_id", ""), trace.get("title", ""), trace.get("summary", ""), compact_json(raw)]
            if any(target_lower in str(value).lower() for value in values if value):
                return {"target": target, "match_type": "trace", "trace": trace}
        fact = self.get_fact(target)
        if fact:
            related = self.related_traces(target)
            if related:
                return {"target": target, "match_type": "fact", "trace": related[0]}
        graph_target = self.resolve_graph_target(target)
        for trace in traces:
            raw = json.loads(trace["raw_json"] or "{}")
            blob = compact_json(raw)
            if graph_target["node_id"] and graph_target["node_id"] in blob:
                return {"target": target, "match_type": "graph_target", "trace": trace, "graph_target": graph_target}
        return {"target": target, "match_type": "unmatched", "trace": None}

    def trace_node_sequence(self, trace_raw: dict[str, Any]) -> list[str]:
        nodes = []
        for step in as_list(trace_raw.get("nodes") or trace_raw.get("steps")):
            if isinstance(step, dict):
                node_id = step.get("node_id") or step.get("span_id") or step.get("id") or step.get("target")
                if node_id:
                    nodes.append(str(node_id))
            elif step:
                nodes.append(str(step))
        return nodes

    def facts_for_trace(self, trace: dict[str, Any]) -> list[dict[str, Any]]:
        raw = json.loads(trace["raw_json"] or "{}")
        explicit = {str(x) for x in as_list(raw.get("fact_ids")) if x}
        trace_blob = compact_json(raw)
        with self.connect() as conn:
            facts = conn.execute("select * from facts").fetchall()
            evidence_rows = conn.execute("select * from evidence").fetchall()
        by_fact: dict[str, list[sqlite3.Row]] = {}
        for ev in evidence_rows:
            by_fact.setdefault(ev["fact_id"], []).append(ev)
        related: list[dict[str, Any]] = []
        for fact in facts:
            evs = by_fact.get(fact["fact_id"], [])
            if fact["fact_id"] in explicit or fact["fact_id"] in trace_blob or any(ev["span_id"] and ev["span_id"] in trace_blob for ev in evs):
                related.append(dict(fact))
        return related

    def trace_report(self, target: str) -> dict[str, Any]:
        resolved = self.resolve_trace_target(target)
        trace = resolved.get("trace")
        if not trace:
            return {"matched_target": resolved, "graph_path": {"found": False, "nodes": [], "edges": []}, "related_facts": [], "evidence_files": [], "confidence": "unknown", "related_tests": []}
        raw = json.loads(trace["raw_json"] or "{}")
        sequence = self.trace_node_sequence(raw)
        graph_path: dict[str, Any]
        if len(sequence) >= 2:
            graph_path = self.graph_path(sequence[0], sequence[-1], max_depth=max(len(sequence) + 2, 6))
            if not graph_path["found"]:
                graph_path = {"found": True, "nodes": [{"node_id": node_id, "node": self.resolve_graph_target(node_id).get("node", {})} for node_id in sequence], "edges": []}
        elif sequence:
            graph_path = {"found": True, "nodes": [{"node_id": sequence[0], "node": self.resolve_graph_target(sequence[0]).get("node", {})}], "edges": []}
        else:
            graph_path = {"found": False, "nodes": [], "edges": []}
        facts = self.facts_for_trace(trace)
        evidence_files: set[str] = set()
        tests: set[str] = {str(x) for x in as_list(raw.get("related_tests") or raw.get("tests")) if x}
        for fact in facts:
            for ev in self.get_evidence(fact["fact_id"]):
                if ev["path"]:
                    evidence_files.add(ev["path"])
            tests.update(self.related_tests(fact["fact_id"]))
        return {
            "matched_target": {key: value for key, value in resolved.items() if key != "trace"},
            "trace": trace,
            "graph_path": graph_path,
            "related_facts": facts,
            "evidence_files": sorted(evidence_files),
            "confidence": trace.get("confidence") or raw.get("confidence") or "unknown",
            "related_tests": sorted(tests),
        }


