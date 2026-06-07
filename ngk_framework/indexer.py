from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

import yaml

from .base import Evidence, Fact, Workspace, as_list, compact_json, get_id, json_pointer, load_yaml_or_json, read_jsonl, write_jsonl

class AtlasIndexer:
    def __init__(self, ws: Workspace) -> None:
        self.ws = ws

    def connect(self) -> sqlite3.Connection:
        self.ws.cache.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.ws.db)
        conn.row_factory = sqlite3.Row
        return conn

    def reset_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            drop table if exists facts;
            drop table if exists evidence;
            drop table if exists source_spans;
            drop table if exists traces;
            drop table if exists nodes;
            drop table if exists edges;
            drop table if exists retrieval_items;
            create table facts(
              fact_id text primary key,
              claim text,
              type text,
              confidence text,
              atlas_file text,
              atlas_pointer text,
              subject_id text,
              raw_json text
            );
            create table evidence(
              evidence_id text primary key,
              fact_id text,
              repo_id text,
              path text,
              start_line integer,
              end_line integer,
              pointer text,
              method text,
              span_id text
            );
            create table source_spans(
              span_id text primary key,
              repo_id text,
              file_id text,
              path text,
              language text,
              start_line integer,
              end_line integer,
              content_hash text,
              raw_json text
            );
            create table traces(
              trace_id text primary key,
              title text,
              summary text,
              confidence text,
              raw_json text
            );
            create table nodes(
              node_id text primary key,
              label text,
              kind text,
              path text,
              symbol text,
              raw_json text
            );
            create table edges(
              edge_id text primary key,
              from_id text,
              to_id text,
              type text,
              confidence text,
              raw_json text
            );
            create table retrieval_items(
              item_id text primary key,
              item_type text,
              title text,
              text text,
              path text,
              symbol text,
              route text,
              trace_id text,
              fact_id text,
              priority real,
              raw_json text
            );
            """
        )

    def iter_fact_files(self) -> Iterable[Path]:
        facts_dir = self.ws.atlas / "facts"
        if not facts_dir.exists():
            return []
        return sorted(p for p in facts_dir.rglob("*") if p.suffix.lower() in {".yaml", ".yml", ".json"})

    def iter_jsonl_files(self, dirname: str) -> list[Path]:
        artifact_dir = self.ws.atlas / dirname
        if not artifact_dir.exists():
            return []
        return sorted(artifact_dir.rglob("*.jsonl"))

    def normalize_evidence(self, fact_id: str, item: dict[str, Any], index: int) -> Evidence:
        lines = item.get("lines") or item.get("line_range") or item.get("range") or []
        start_line = item.get("start_line")
        end_line = item.get("end_line")
        if isinstance(lines, list) and len(lines) >= 2:
            start_line, end_line = lines[0], lines[1]
        return Evidence(
            evidence_id=str(item.get("evidence_id") or item.get("id") or f"evidence.{fact_id}.{index}"),
            fact_id=fact_id,
            path=str(item.get("path") or item.get("file") or item.get("file_path") or ""),
            start_line=int(start_line) if start_line is not None else None,
            end_line=int(end_line) if end_line is not None else None,
            pointer=str(item.get("pointer") or ""),
            method=str(item.get("method") or item.get("extracted_by") or ""),
            span_id=str(item.get("span_id") or ""),
            repo_id=str(item.get("repo_id") or item.get("repo") or ""),
        )

    def load_facts(self) -> tuple[list[Fact], list[Evidence]]:
        facts: list[Fact] = []
        evidence: list[Evidence] = []
        for path in self.iter_fact_files():
            try:
                data = load_yaml_or_json(path)
            except (OSError, json.JSONDecodeError, yaml.YAMLError):
                continue
            if isinstance(data, dict):
                fact_rows = data.get("facts", []) or data.get("items", [])
            elif isinstance(data, list):
                fact_rows = data
            else:
                fact_rows = []
            for idx, row in enumerate(fact_rows):
                if not isinstance(row, dict):
                    continue
                fact_id = get_id(row, "id", "fact_id")
                if not fact_id:
                    continue
                subject = row.get("subject") or {}
                subject_id = subject.get("id") if isinstance(subject, dict) else row.get("subject_id", "")
                pointer = str(row.get("atlas_pointer") or json_pointer(path, "facts", idx))
                facts.append(
                    Fact(
                        fact_id=fact_id,
                        claim=str(row.get("claim") or row.get("summary") or row.get("description") or ""),
                        type=str(row.get("type") or row.get("kind") or "unknown"),
                        confidence=str(row.get("confidence") or "unknown"),
                        atlas_file=path.as_posix(),
                        atlas_pointer=pointer,
                        subject_id=str(subject_id or ""),
                        raw=row,
                    )
                )
                for eidx, item in enumerate(as_list(row.get("evidence"))):
                    if isinstance(item, dict):
                        evidence.append(self.normalize_evidence(fact_id, item, eidx))
        return facts, evidence

    def load_source_spans(self) -> list[dict[str, Any]]:
        spans: list[dict[str, Any]] = []
        seen: set[str] = set()
        for path in self.iter_jsonl_files("indexes") + [self.ws.atlas / "source_spans.jsonl"]:
            if path.name != "source_spans.jsonl":
                continue
            for row in read_jsonl(path):
                span_id = get_id(row, "span_id", "id")
                if span_id and span_id not in seen:
                    row.setdefault("span_id", span_id)
                    spans.append(row)
                    seen.add(span_id)
        return spans

    def load_traces(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        traces_dir = self.ws.atlas / "traces"
        if traces_dir.exists():
            for p in sorted(traces_dir.rglob("*.jsonl")):
                for row in read_jsonl(p):
                    trace_id = get_id(row, "trace_id", "id")
                    if trace_id and trace_id not in seen:
                        row.setdefault("trace_id", trace_id)
                        rows.append(row)
                        seen.add(trace_id)
            for p in sorted(traces_dir.rglob("*.json")):
                try:
                    data = load_yaml_or_json(p)
                except (OSError, json.JSONDecodeError):
                    continue
                candidates = data if isinstance(data, list) else data.get("traces", []) if isinstance(data, dict) else []
                for row in candidates:
                    if isinstance(row, dict):
                        trace_id = get_id(row, "trace_id", "id")
                        if trace_id and trace_id not in seen:
                            row.setdefault("trace_id", trace_id)
                            rows.append(row)
                            seen.add(trace_id)
        return rows

    def load_graph(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        seen_nodes: set[str] = set()
        seen_edges: set[str] = set()
        for path in self.iter_jsonl_files("graph"):
            for row in read_jsonl(path):
                if self.is_edge(row, path):
                    edge_id = get_id(row, "edge_id", "id") or f"edge.{len(edges) + 1}"
                    if edge_id not in seen_edges:
                        row.setdefault("edge_id", edge_id)
                        edges.append(row)
                        seen_edges.add(edge_id)
                else:
                    node_id = get_id(row, "node_id", "id", "symbol_id")
                    if node_id and node_id not in seen_nodes:
                        row.setdefault("node_id", node_id)
                        nodes.append(row)
                        seen_nodes.add(node_id)
        return nodes, edges

    def is_edge(self, row: dict[str, Any], path: Path) -> bool:
        if path.name.startswith("edge"):
            return True
        if path.name.startswith("node"):
            return False
        return any(k in row for k in ("edge_id", "from", "to", "from_id", "to_id", "source", "target"))

    def load_external_retrieval_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in self.iter_jsonl_files("indexes"):
            if path.name == "source_spans.jsonl":
                continue
            for idx, row in enumerate(read_jsonl(path)):
                item_id = get_id(row, "item_id", "id") or f"{path.stem}.{idx}"
                item_type = str(row.get("item_type") or row.get("type") or path.stem)
                text = str(row.get("text") or row.get("claim") or row.get("summary") or row.get("content") or compact_json(row))
                items.append(
                    {
                        "item_id": item_id,
                        "item_type": item_type,
                        "title": str(row.get("title") or row.get("label") or item_id),
                        "text": text,
                        "path": str(row.get("path") or ""),
                        "symbol": str(row.get("symbol") or row.get("symbol_id") or ""),
                        "route": str(row.get("route") or ""),
                        "trace_id": str(row.get("trace_id") or ""),
                        "fact_id": str(row.get("fact_id") or ""),
                        "priority": float(row.get("priority") or 0.25),
                        "raw_json": compact_json(row),
                    }
                )
        return items

    def build_retrieval_items(
        self,
        facts: list[Fact],
        evidence: list[Evidence],
        spans: list[dict[str, Any]],
        traces: list[dict[str, Any]],
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        ev_by_fact: dict[str, list[Evidence]] = {}
        for e in evidence:
            ev_by_fact.setdefault(e.fact_id, []).append(e)
        items = self.load_external_retrieval_items()
        seen = {str(item["item_id"]) for item in items}

        def add(row: dict[str, Any]) -> None:
            if row["item_id"] in seen:
                return
            items.append(row)
            seen.add(row["item_id"])

        for f in facts:
            evs = ev_by_fact.get(f.fact_id, [])
            raw = f.raw or {}
            subject = raw.get("subject") if isinstance(raw.get("subject"), dict) else {}
            route = str(raw.get("route") or subject.get("name") or "") if ("/" in str(subject.get("name") or raw.get("route") or "")) else ""
            add(
                {
                    "item_id": f.fact_id,
                    "item_type": "fact",
                    "title": f.fact_id,
                    "text": " ".join([f.fact_id, f.type, f.claim, f.subject_id, " ".join(e.path for e in evs), compact_json(raw)]),
                    "path": " ".join(e.path for e in evs),
                    "symbol": f.subject_id,
                    "route": route,
                    "trace_id": " ".join(str(x) for x in as_list((raw.get("related") or {}).get("traces") if isinstance(raw.get("related"), dict) else [])),
                    "fact_id": f.fact_id,
                    "priority": 1.0 if f.confidence == "high" else 0.5,
                    "raw_json": compact_json(raw),
                }
            )
        for span in spans:
            span_id = str(span.get("span_id"))
            add(
                {
                    "item_id": span_id,
                    "item_type": "source_span",
                    "title": span_id,
                    "text": " ".join(str(span.get(k, "")) for k in ("span_id", "repo_id", "file_id", "path", "language")) + " " + compact_json(span),
                    "path": str(span.get("path") or ""),
                    "symbol": str(span.get("symbol") or ""),
                    "route": str(span.get("route") or ""),
                    "trace_id": "",
                    "fact_id": "",
                    "priority": 0.4,
                    "raw_json": compact_json(span),
                }
            )
        for trace in traces:
            trace_id = str(trace.get("trace_id"))
            add(
                {
                    "item_id": trace_id,
                    "item_type": "trace",
                    "title": str(trace.get("title") or trace_id),
                    "text": " ".join([trace_id, str(trace.get("title", "")), str(trace.get("summary", "")), compact_json(trace)]),
                    "path": "",
                    "symbol": " ".join(str(step.get("span_id") or step.get("node_id") or "") for step in as_list(trace.get("steps") or trace.get("nodes")) if isinstance(step, dict)),
                    "route": str(trace.get("route") or ""),
                    "trace_id": trace_id,
                    "fact_id": " ".join(str(x) for x in as_list(trace.get("fact_ids"))),
                    "priority": 0.8 if trace.get("confidence") == "high" else 0.45,
                    "raw_json": compact_json(trace),
                }
            )
        for node in nodes:
            node_id = str(node.get("node_id"))
            add(
                {
                    "item_id": node_id,
                    "item_type": "node",
                    "title": str(node.get("label") or node.get("name") or node_id),
                    "text": compact_json(node),
                    "path": str(node.get("path") or ""),
                    "symbol": str(node.get("symbol") or node_id),
                    "route": str(node.get("route") or ""),
                    "trace_id": "",
                    "fact_id": " ".join(str(x) for x in as_list(node.get("fact_ids"))),
                    "priority": 0.35,
                    "raw_json": compact_json(node),
                }
            )
        for edge in edges:
            edge_id = str(edge.get("edge_id"))
            add(
                {
                    "item_id": edge_id,
                    "item_type": "edge",
                    "title": edge_id,
                    "text": compact_json(edge),
                    "path": "",
                    "symbol": " ".join(str(edge.get(k, "")) for k in ("from", "from_id", "to", "to_id", "source", "target")),
                    "route": str(edge.get("route") or ""),
                    "trace_id": "",
                    "fact_id": " ".join(str(x) for x in as_list(edge.get("fact_ids"))),
                    "priority": 0.3,
                    "raw_json": compact_json(edge),
                }
            )
        return items

    def index(self) -> dict[str, int]:
        facts, evidence = self.load_facts()
        spans = self.load_source_spans()
        traces = self.load_traces()
        nodes, edges = self.load_graph()
        retrieval_items = self.build_retrieval_items(facts, evidence, spans, traces, nodes, edges)
        with self.connect() as conn:
            self.reset_schema(conn)
            conn.executemany(
                "insert or replace into facts values (?,?,?,?,?,?,?,?)",
                [(f.fact_id, f.claim, f.type, f.confidence, f.atlas_file, f.atlas_pointer, f.subject_id, json.dumps(f.raw or {}, ensure_ascii=False)) for f in facts],
            )
            conn.executemany(
                "insert or replace into evidence values (?,?,?,?,?,?,?,?,?)",
                [(e.evidence_id, e.fact_id, e.repo_id, e.path, e.start_line, e.end_line, e.pointer, e.method, e.span_id) for e in evidence],
            )
            conn.executemany(
                "insert or replace into source_spans values (?,?,?,?,?,?,?,?,?)",
                [(s.get("span_id"), s.get("repo_id", ""), s.get("file_id", ""), s.get("path", ""), s.get("language", ""), s.get("start_line"), s.get("end_line"), s.get("content_hash", ""), json.dumps(s, ensure_ascii=False)) for s in spans if s.get("span_id")],
            )
            conn.executemany(
                "insert or replace into traces values (?,?,?,?,?)",
                [(t.get("trace_id"), t.get("title", ""), t.get("summary", ""), t.get("confidence", ""), json.dumps(t, ensure_ascii=False)) for t in traces if t.get("trace_id")],
            )
            conn.executemany(
                "insert or replace into nodes values (?,?,?,?,?,?)",
                [(n.get("node_id"), n.get("label") or n.get("name", ""), n.get("kind") or n.get("type", ""), n.get("path", ""), n.get("symbol") or n.get("node_id", ""), json.dumps(n, ensure_ascii=False)) for n in nodes if n.get("node_id")],
            )
            conn.executemany(
                "insert or replace into edges values (?,?,?,?,?,?)",
                [(e.get("edge_id"), e.get("from") or e.get("from_id") or e.get("source", ""), e.get("to") or e.get("to_id") or e.get("target", ""), e.get("type") or e.get("kind", ""), e.get("confidence", ""), json.dumps(e, ensure_ascii=False)) for e in edges if e.get("edge_id")],
            )
            conn.executemany(
                "insert or replace into retrieval_items values (?,?,?,?,?,?,?,?,?,?,?)",
                [(r["item_id"], r["item_type"], r["title"], r["text"], r["path"], r["symbol"], r["route"], r["trace_id"], r["fact_id"], r["priority"], r["raw_json"]) for r in retrieval_items],
            )
        self.write_indexes(facts, evidence, traces, retrieval_items)
        return {"facts": len(facts), "evidence": len(evidence), "spans": len(spans), "traces": len(traces), "nodes": len(nodes), "edges": len(edges), "retrieval_items": len(retrieval_items)}

    def write_indexes(self, facts: list[Fact], evidence: list[Evidence], traces: list[dict[str, Any]], retrieval_items: list[dict[str, Any]]) -> None:
        ev_by_fact: dict[str, list[Evidence]] = {}
        for e in evidence:
            ev_by_fact.setdefault(e.fact_id, []).append(e)
        citation_rows = []
        source_cards = []
        for f in facts:
            evs = ev_by_fact.get(f.fact_id, [])
            citation_rows.append({**asdict(f), "evidence": [asdict(e) for e in evs]})
            source_cards.append({"card_id": f"source_card.{f.fact_id}", "fact_id": f.fact_id, "title": f.fact_id, "claim": f.claim, "confidence": f.confidence, "atlas_source": f.atlas_pointer, "evidence_sources": [asdict(e) for e in evs]})
        trace_cards = []
        for t in traces:
            trace_cards.append({"card_id": f"trace_card.{t.get('trace_id')}", "trace_id": t.get("trace_id"), "title": t.get("title", ""), "summary": t.get("summary", ""), "confidence": t.get("confidence", ""), "steps": t.get("steps") or t.get("nodes") or [], "related_tests": t.get("related_tests") or t.get("tests") or []})
        write_jsonl(self.ws.cache / "citation_index.jsonl", citation_rows)
        write_jsonl(self.ws.cache / "source_cards.jsonl", source_cards)
        write_jsonl(self.ws.cache / "retrieval_index.jsonl", retrieval_items)
        write_jsonl(self.ws.cache / "trace_cards.jsonl", trace_cards)


