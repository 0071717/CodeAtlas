#!/usr/bin/env python3
"""Atlas-native ngk framework.

Indexes Atlas facts, traces, graph artifacts, and retrieval indexes into a small
SQLite read model plus JSONL caches that can be inspected by ngk commands.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

FACT_ID_RE = re.compile(r"\bfact\.[A-Za-z0-9_.:/-]+")
INLINE_FACT_ID_RE = re.compile(r"\[(fact\.[A-Za-z0-9_.:/-]+)\]")
CITATION_BLOCK_RE = re.compile(r"<atlas_citations>\s*(.*?)\s*</atlas_citations>", re.S)
TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]+")


def now_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file, skipping malformed or non-object rows.

    Atlas artifact directories are optional and may contain experimental files.
    ngk should still build every usable part of the cache when one row is bad.
    """
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def load_yaml_or_json(path: Path) -> Any:
    text = read_text(path)
    if path.suffix.lower() == ".json":
        return json.loads(text)
    return yaml.safe_load(text) or {}


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def get_id(row: dict[str, Any], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value:
            return str(value)
    return ""


def json_pointer(path: Path, key: str, index: int) -> str:
    return f"{path.as_posix()}#/{key}/{index}"


def compact_json(row: dict[str, Any]) -> str:
    return json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def clean_fact_id(value: Any) -> str:
    return str(value).strip().rstrip(".,;:)]}>")


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def valid_sha256(value: str) -> bool:
    return bool(re.fullmatch(r"sha256:[0-9a-fA-F]{64}", value or ""))


def file_hash_candidates(path: Path, start_line: int | None = None, end_line: int | None = None) -> set[str]:
    """Return whole-file and span-content hashes for a source file.

    Atlas producers have historically hashed either entire files or the exact
    line-addressed source span. Supporting both keeps drift checks compatible
    across skeleton artifacts without making missing hash metadata fatal.
    """
    data = path.read_bytes()
    hashes = {sha256_bytes(data)}
    if start_line is not None and end_line is not None:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        selected = lines[max(start_line - 1, 0) : min(end_line, len(lines))]
        span_text = "\n".join(selected)
        hashes.add(sha256_bytes(span_text.encode("utf-8")))
        hashes.add(sha256_bytes((span_text + "\n").encode("utf-8")))
    return hashes


@dataclass
class Evidence:
    evidence_id: str
    fact_id: str
    path: str = ""
    start_line: int | None = None
    end_line: int | None = None
    pointer: str = ""
    method: str = ""
    span_id: str = ""
    repo_id: str = ""


@dataclass
class Fact:
    fact_id: str
    claim: str
    type: str = "unknown"
    confidence: str = "unknown"
    atlas_file: str = ""
    atlas_pointer: str = ""
    subject_id: str = ""
    raw: dict[str, Any] | None = None


class Workspace:
    def __init__(self, root: Path, atlas_dir: str = ".atlas", ngk_dir: str = ".ngk") -> None:
        self.root = root.resolve()
        self.atlas = (self.root / atlas_dir).resolve()
        self.ngk = (self.root / ngk_dir).resolve()
        self.cache = self.ngk / "cache"
        self.sessions = self.ngk / "sessions"
        self.db = self.cache / "atlas.db"
        self.source_root = self.atlas.parent if self.atlas.name == ".atlas" else self.root


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


class OutputParser:
    """Parse Atlas citations from generated answers.

    Preferred output is an <atlas_citations> JSON block. For compatibility with
    older answers, inline [fact.some.id] citations are recognized before falling
    back to broad fact-id scanning.
    """

    def parse(self, text: str) -> dict[str, Any]:
        block = CITATION_BLOCK_RE.search(text)
        if block:
            try:
                payload = json.loads(block.group(1))
            except json.JSONDecodeError:
                payload = {}
            else:
                fact_ids = self.fact_ids_from_payload(payload)
                if not fact_ids:
                    fact_ids = sorted({clean_fact_id(x) for x in FACT_ID_RE.findall(text) if clean_fact_id(x)})
                return {
                    "format": "atlas_citations",
                    "fact_ids": fact_ids,
                    "payload": payload,
                    "claims": self.claims_from_payload(payload),
                    "not_confirmed": self.not_confirmed_from_payload(payload),
                }
        inline = sorted({clean_fact_id(x) for x in INLINE_FACT_ID_RE.findall(text) if clean_fact_id(x)})
        if inline:
            return {"format": "inline_brackets", "fact_ids": inline, "payload": {}, "claims": [], "not_confirmed": []}
        fallback = sorted({clean_fact_id(x) for x in FACT_ID_RE.findall(text) if clean_fact_id(x)})
        return {"format": "fallback_scan", "fact_ids": fallback, "payload": {}, "claims": [], "not_confirmed": []}

    def fact_ids_from_payload(self, payload: dict[str, Any]) -> list[str]:
        fact_ids: set[str] = set()
        for citation in as_list(payload.get("citations")):
            if isinstance(citation, dict):
                fact_ids.update(clean_fact_id(x) for x in as_list(citation.get("fact_id") or citation.get("fact_ids")) if clean_fact_id(x))
            elif citation:
                fact_ids.add(clean_fact_id(citation))
        for claim in self.claims_from_payload(payload):
            fact_ids.update(clean_fact_id(x) for x in as_list(claim.get("fact_ids")) if clean_fact_id(x))
        return sorted(fact_ids)

    def claims_from_payload(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        return [claim for claim in as_list(payload.get("claims")) if isinstance(claim, dict)]

    def not_confirmed_from_payload(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        rows = [claim for claim in as_list(payload.get("not_confirmed")) if isinstance(claim, dict)]
        for claim in self.claims_from_payload(payload):
            if str(claim.get("support") or "").lower() in {"not_confirmed", "not-confirmed", "unsupported"}:
                rows.append(claim)
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for row in rows:
            key = compact_json(row)
            if key not in seen:
                deduped.append(row)
                seen.add(key)
        return deduped


def parse_citations(text: str) -> dict[str, Any]:
    return OutputParser().parse(text)


class AuditEngine:
    def __init__(self, ws: Workspace) -> None:
        self.ws = ws
        self.store = AtlasStore(ws)

    def stale_fact_ids(self) -> tuple[set[str], list[dict[str, Any]]]:
        report = evaluate_drift(self.ws)
        stale = {fact_id for issue in report.get("issues", []) for fact_id in issue.get("affected_fact_ids", [])}
        return stale, report.get("issues", [])

    def audit_text(self, text: str) -> dict[str, Any]:
        parsed = parse_citations(text)
        stale_ids, drift_issues = self.stale_fact_ids()
        resolved: list[str] = []
        missing: list[str] = []
        facts_without_evidence: list[str] = []
        stale_fact_ids: list[str] = []
        fact_checks: list[dict[str, Any]] = []
        for fact_id in parsed["fact_ids"]:
            fact = self.store.get_fact(fact_id)
            evidence = self.store.get_evidence(fact_id) if fact else []
            exists = fact is not None
            has_evidence = bool(evidence)
            is_stale = fact_id in stale_ids
            if exists:
                resolved.append(fact_id)
            else:
                missing.append(fact_id)
            if exists and not has_evidence:
                facts_without_evidence.append(fact_id)
            if exists and is_stale:
                stale_fact_ids.append(fact_id)
            fact_checks.append({"fact_id": fact_id, "exists": exists, "has_evidence": has_evidence, "stale": is_stale})

        unsupported_claims = self.unsupported_claims(parsed, set(resolved), set(missing), set(facts_without_evidence), set(stale_fact_ids))
        status = "passed" if not (missing or facts_without_evidence or stale_fact_ids or unsupported_claims) else "failed"
        return {
            "status": status,
            "citation_format": parsed["format"],
            "resolved_fact_ids": resolved,
            "missing_fact_ids": missing,
            "facts_without_evidence": sorted(facts_without_evidence),
            "stale_fact_ids": sorted(stale_fact_ids),
            "fact_checks": fact_checks,
            "unsupported_claims": unsupported_claims,
            "not_confirmed": parsed.get("not_confirmed", []),
            "drift_issues": [issue for issue in drift_issues if set(issue.get("affected_fact_ids", [])) & set(parsed["fact_ids"])],
        }

    def unsupported_claims(
        self,
        parsed: dict[str, Any],
        resolved: set[str],
        missing: set[str],
        no_evidence: set[str],
        stale: set[str],
    ) -> list[dict[str, Any]]:
        unsupported: list[dict[str, Any]] = []
        not_confirmed_keys = {str(row.get("claim_id") or row.get("text") or compact_json(row)) for row in parsed.get("not_confirmed", []) if isinstance(row, dict)}
        for idx, claim in enumerate(parsed.get("claims", []), 1):
            claim_id = str(claim.get("claim_id") or f"claim.{idx}")
            key = str(claim.get("claim_id") or claim.get("text") or compact_json(claim))
            support = str(claim.get("support") or "supported").lower()
            if support in {"not_confirmed", "not-confirmed", "unsupported"} or key in not_confirmed_keys:
                continue
            fact_ids = {clean_fact_id(x) for x in as_list(claim.get("fact_ids")) if clean_fact_id(x)}
            reasons: list[str] = []
            if not fact_ids:
                reasons.append("claim has no fact_ids")
            bad_missing = sorted(fact_ids & missing)
            bad_no_evidence = sorted(fact_ids & no_evidence)
            bad_stale = sorted(fact_ids & stale)
            if bad_missing:
                reasons.append("missing cited facts: " + ",".join(bad_missing))
            if bad_no_evidence:
                reasons.append("cited facts lack evidence: " + ",".join(bad_no_evidence))
            if bad_stale:
                reasons.append("cited facts have stale sources: " + ",".join(bad_stale))
            if fact_ids and not (fact_ids & resolved):
                reasons.append("claim is not supported by any resolved Atlas fact")
            if reasons:
                unsupported.append({"claim_id": claim_id, "text": claim.get("text", ""), "fact_ids": sorted(fact_ids), "reasons": reasons})
        if not parsed.get("claims") and not parsed.get("fact_ids") and not parsed.get("not_confirmed"):
            unsupported.append({"claim_id": "answer", "text": "Answer contains no Atlas citations", "fact_ids": [], "reasons": ["no Atlas fact IDs were cited"]})
        return unsupported

    def audit_file(self, answer_path: Path) -> dict[str, Any]:
        audit = self.audit_text(read_text(answer_path))
        write_text(answer_path.parent / "audit.json", json.dumps(audit, indent=2))
        return audit



class ContextPackBuilder:
    """Build compact, evidence-backed Kiro context packs from Atlas cache data."""

    def __init__(self, ws: Workspace) -> None:
        self.ws = ws
        self.store = AtlasStore(ws)

    def evidence_for_fact(self, fact_id: str) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        for ev in self.store.get_evidence(fact_id):
            row = dict(ev)
            span = self.store.get_source_span(ev["span_id"])
            if span:
                row["source_span"] = dict(span)
            evidence.append(row)
        return evidence

    def select_facts(self, request: str, limit: int) -> list[dict[str, Any]]:
        facts: list[dict[str, Any]] = []
        for rank, row in enumerate(self.store.search_facts(request, limit=limit), 1):
            fact = dict(row)
            fact["selection_reason"] = f"matched user task search terms (rank {rank})"
            fact["evidence"] = self.evidence_for_fact(fact["fact_id"])
            fact["related_tests"] = self.store.related_tests(fact["fact_id"])
            facts.append(fact)
        return facts

    def select_traces(self, request: str, facts: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        traces: dict[str, dict[str, Any]] = {}
        for fact in facts:
            for trace in self.store.related_traces(fact["fact_id"]):
                trace_id = trace["trace_id"]
                item = traces.setdefault(trace_id, {**trace, "selection_reasons": [], "related_fact_ids": []})
                item["selection_reasons"].append(f"related to selected fact {fact['fact_id']}")
                item["related_fact_ids"].append(fact["fact_id"])
        for hit in self.store.search(request, limit=limit):
            if hit.get("item_type") != "trace" or not hit.get("trace_id"):
                continue
            trace_report = self.store.trace_report(str(hit["trace_id"]))
            trace = trace_report.get("trace")
            if not trace:
                continue
            trace_id = trace["trace_id"]
            item = traces.setdefault(trace_id, {**trace, "selection_reasons": [], "related_fact_ids": []})
            item["selection_reasons"].append("matched user task retrieval search")
        for item in traces.values():
            item["selection_reasons"] = sorted(set(item["selection_reasons"]))
            item["related_fact_ids"] = sorted(set(item["related_fact_ids"]))
            raw = row_raw(item)
            item["related_tests"] = sorted(str(x) for x in as_list(raw.get("related_tests") or raw.get("tests")) if x)
        return sorted(traces.values(), key=lambda trace: trace["trace_id"])[:limit]

    def known_gaps(self, facts: list[dict[str, Any]], traces: list[dict[str, Any]], drift: dict[str, Any]) -> dict[str, Any]:
        gaps = {
            "facts_without_evidence": sorted(fact["fact_id"] for fact in facts if not fact.get("evidence")),
            "facts_without_related_tests": sorted(fact["fact_id"] for fact in facts if not fact.get("related_tests")),
            "traces_without_related_tests": sorted(trace["trace_id"] for trace in traces if not trace.get("related_tests")),
            "drift_issue_count": drift.get("issue_count", 0),
        }
        if not facts:
            gaps["no_selected_facts"] = True
        return gaps

    def build_payload(self, mode: str, request: str, limit: int) -> dict[str, Any]:
        facts = self.select_facts(request, limit)
        traces = self.select_traces(request, facts, limit)
        drift = evaluate_drift(self.ws)
        tests = sorted({test for fact in facts for test in fact.get("related_tests", [])} | {test for trace in traces for test in trace.get("related_tests", [])})
        return {
            "mode": mode,
            "request": request,
            "created_at": now_id(),
            "drift": {"status": drift.get("status"), "issue_count": drift.get("issue_count"), "issues": drift.get("issues", [])[:10]},
            "facts": facts,
            "traces": traces,
            "related_tests": tests,
            "known_gaps": self.known_gaps(facts, traces, drift),
            "citation_schema": {
                "claims": [{"claim_id": "claim.1", "text": "...", "support": "supported|not_confirmed", "fact_ids": ["fact.example"]}],
                "citations": [{"fact_id": "fact.example", "used_for_claims": ["claim.1"]}],
                "not_confirmed": [{"claim_id": "claim.n", "text": "...", "reason": "No Atlas fact/evidence in context pack confirms this."}],
            },
        }

    def render_markdown(self, payload: dict[str, Any]) -> str:
        lines = [
            "# ngk / Atlas Kiro context pack",
            "",
            f"Mode: {payload['mode']}",
            "",
            "## User task",
            "",
            payload["request"],
            "",
            "## Atlas drift status",
            "",
            f"Status: {payload['drift']['status']} ({payload['drift']['issue_count']} issue(s))",
        ]
        for issue in payload["drift"].get("issues", [])[:5]:
            lines.append(f"- {issue.get('type')}: {issue.get('message')}")
        lines.extend([
            "",
            "## Strict Kiro citation rules",
            "",
            "- Use only the selected Atlas facts, traces, tests, and source evidence in this pack for architectural/API/UI/data/model/test claims.",
            "- Cite every supported technical claim with Atlas fact IDs from this pack.",
            "- Do not cite traces or source paths as substitutes for fact IDs; use them only as evidence context.",
            "- If this pack does not confirm a claim, write: Not confirmed by Atlas.",
            "- End the answer with exactly one machine-readable <atlas_citations> JSON block matching the required schema.",
            "",
            "## Selected facts",
            "",
        ])
        if not payload["facts"]:
            lines.append("No Atlas facts were selected for this task.")
        for fact in payload["facts"]:
            lines.extend([
                f"### {fact['fact_id']}",
                f"Selection reason: {fact.get('selection_reason', 'selected')}",
                f"Claim: {fact.get('claim', '')}",
                f"Confidence: {fact.get('confidence', 'unknown')}",
                f"Atlas source: {fact.get('atlas_pointer') or fact.get('atlas_file') or 'unknown'}",
                "Source evidence:",
            ])
            if not fact.get("evidence"):
                lines.append("- No source evidence indexed.")
            for ev in fact.get("evidence", []):
                loc = ev.get("path") or ev.get("pointer") or ev.get("span_id") or "unknown"
                if ev.get("start_line") and ev.get("end_line"):
                    loc += f":{ev['start_line']}-{ev['end_line']}"
                method = ev.get("method") or "unknown_method"
                span = ev.get("source_span") or {}
                span_hash = f" hash={span.get('content_hash')}" if span.get("content_hash") else ""
                lines.append(f"- {loc} ({method}) span={ev.get('span_id') or 'none'}{span_hash}")
            if fact.get("related_tests"):
                lines.append("Related tests:")
                for test in fact["related_tests"]:
                    lines.append(f"- {test}")
            lines.append("")
        lines.extend(["## Selected traces", ""])
        if not payload["traces"]:
            lines.append("No Atlas traces were selected for this task.")
        for trace in payload["traces"]:
            raw = row_raw(trace)
            lines.extend([
                f"### {trace['trace_id']}",
                f"Selection reasons: {', '.join(trace.get('selection_reasons') or ['selected'])}",
                f"Title: {trace.get('title', '')}",
                f"Summary: {trace.get('summary', '')}",
                f"Confidence: {trace.get('confidence') or raw.get('confidence') or 'unknown'}",
            ])
            steps = as_list(raw.get("steps") or raw.get("nodes"))
            if steps:
                lines.append("Steps:")
                for step in steps[:12]:
                    lines.append(f"- {compact_json(step) if isinstance(step, dict) else step}")
            if trace.get("related_tests"):
                lines.append("Related tests:")
                for test in trace["related_tests"]:
                    lines.append(f"- {test}")
            lines.append("")
        lines.extend(["## Related tests", ""])
        if payload["related_tests"]:
            lines.extend(f"- {test}" for test in payload["related_tests"])
        else:
            lines.append("No related tests were selected from Atlas metadata.")
        lines.extend(["", "## Known gaps", ""])
        gaps = payload["known_gaps"]
        for key, value in gaps.items():
            lines.append(f"- {key}: {json.dumps(value, ensure_ascii=False)}")
        lines.extend([
            "",
            "## Required <atlas_citations> JSON schema",
            "",
            "```json",
            json.dumps(payload["citation_schema"], indent=2),
            "```",
            "",
            "Return the schema inside <atlas_citations>...</atlas_citations> in your final answer.",
        ])
        return "\n".join(lines) + "\n"

    def write(self, mode: str, request: str, limit: int = 30) -> Path:
        payload = self.build_payload(mode, request, limit)
        session_id = f"{now_id()}-{mode}"
        session_dir = self.ws.sessions / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        payload["session_id"] = session_id
        write_text(session_dir / "context-pack.md", self.render_markdown(payload))
        write_text(session_dir / "context-pack.json", json.dumps(payload, indent=2))
        write_jsonl(session_dir / "selected-facts.jsonl", payload["facts"])
        write_jsonl(session_dir / "selected-traces.jsonl", payload["traces"])
        explain = {
            "session_id": session_id,
            "facts": [{"fact_id": fact["fact_id"], "reason": fact.get("selection_reason", "selected")} for fact in payload["facts"]],
            "traces": [{"trace_id": trace["trace_id"], "reasons": trace.get("selection_reasons", [])} for trace in payload["traces"]],
            "known_gaps": payload["known_gaps"],
        }
        write_text(session_dir / "selection-explain.json", json.dumps(explain, indent=2))
        write_text(session_dir / "session.json", json.dumps({"session_id": session_id, "mode": mode, "request": request, "created_at": payload["created_at"]}, indent=2))
        write_text(self.ws.sessions / "latest", session_id)
        return session_dir / "context-pack.md"


def build_context(ws: Workspace, mode: str, request: str, limit: int = 30) -> Path:
    return ContextPackBuilder(ws).write(mode, request, limit=limit)


def run_kiro(ws: Workspace, context_pack: Path) -> Path:
    session_dir = context_pack.parent
    cmd_template = os.environ.get("NGK_KIRO_CMD", "")
    if not cmd_template:
        raise SystemExit("NGK_KIRO_CMD is not set. Use --no-agent or export NGK_KIRO_CMD='kiro --prompt-file {context_pack}'")
    if "{context_pack}" in cmd_template:
        cmd = cmd_template.format(context_pack=str(context_pack), session_dir=str(session_dir))
        proc = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    else:
        proc = subprocess.run(cmd_template, shell=True, text=True, input=read_text(context_pack), capture_output=True)
    output = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")
    out_path = session_dir / "kiro-output.raw.md"
    write_text(out_path, output)
    parsed = parse_citations(output)
    write_text(session_dir / "kiro-output.parsed.json", json.dumps(parsed, indent=2))
    write_text(session_dir / "citations.json", json.dumps(parsed, indent=2))
    audit_answer(ws, out_path)
    return out_path


def resolve_session(ws: Workspace, session: str) -> Path:
    if session == "latest":
        latest = ws.sessions / "latest"
        if not latest.exists():
            raise SystemExit("No latest session found")
        session = latest.read_text(encoding="utf-8").strip()
    p = ws.sessions / session
    if not p.exists():
        raise SystemExit(f"Session not found: {session}")
    return p


def audit_answer(ws: Workspace, answer_path: Path) -> dict[str, Any]:
    return AuditEngine(ws).audit_file(answer_path)



def run_git(ws: Workspace, args: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(["git", "-C", str(ws.source_root), *args], text=True, capture_output=True)
    except OSError:
        return 127, ""
    return proc.returncode, proc.stdout.strip()


def current_git_commit(ws: Workspace) -> str:
    code, out = run_git(ws, ["rev-parse", "HEAD"])
    return out if code == 0 else ""


def current_dirty_files(ws: Workspace) -> set[str]:
    code, out = run_git(ws, ["status", "--porcelain=v1", "-z", "--untracked-files=no", "--", "."])
    if code != 0 or not out:
        return set()
    files: set[str] = set()
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


def manifest_commits(ws: Workspace) -> list[dict[str, str]]:
    manifest_path = ws.atlas / "manifest.json"
    if not manifest_path.exists():
        return []
    try:
        data = json.loads(read_text(manifest_path))
    except (OSError, json.JSONDecodeError):
        return []
    commits: list[dict[str, str]] = []

    def add(repo_id: str, commit: Any) -> None:
        if commit:
            commits.append({"repo_id": str(repo_id or "default"), "indexed_commit": str(commit)})

    if isinstance(data, dict):
        for key in ("indexed_commit", "git_commit", "commit", "source_commit", "head_commit"):
            add(str(data.get("repo_id") or data.get("project") or "default"), data.get(key))
        indexed = data.get("indexed_commits") or data.get("commits")
        if isinstance(indexed, dict):
            for repo_id, commit in indexed.items():
                add(str(repo_id), commit)
        elif isinstance(indexed, list):
            for item in indexed:
                if isinstance(item, dict):
                    add(str(item.get("repo_id") or item.get("repo") or item.get("name") or "default"), item.get("commit") or item.get("indexed_commit") or item.get("git_commit"))
        for repo in as_list(data.get("repositories") or data.get("repos")):
            if isinstance(repo, dict):
                add(str(repo.get("repo_id") or repo.get("id") or repo.get("name") or "default"), repo.get("commit") or repo.get("indexed_commit") or repo.get("git_commit"))
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in commits:
        key = (row["repo_id"], row["indexed_commit"])
        if key not in seen:
            deduped.append(row)
            seen.add(key)
    return deduped


def affected_fact_ids_for_paths(store: AtlasStore, paths: Iterable[str]) -> list[str]:
    wanted = {p for p in paths if p}
    if not wanted:
        return []
    with store.connect() as conn:
        rows = conn.execute(
            """
            select distinct e.fact_id
            from evidence e
            left join source_spans s on s.span_id = e.span_id
            where e.path in ({}) or s.path in ({})
            """.format(",".join("?" for _ in wanted), ",".join("?" for _ in wanted)),
            [*wanted, *wanted],
        ).fetchall()
    return sorted(row["fact_id"] for row in rows)


def affected_fact_ids_for_span(store: AtlasStore, span_id: str, path: str) -> list[str]:
    with store.connect() as conn:
        rows = conn.execute(
            "select distinct fact_id from evidence where span_id=? or path=?",
            (span_id, path),
        ).fetchall()
    return sorted(row["fact_id"] for row in rows)


def evaluate_drift(ws: Workspace, *, source_spans_only: bool = False) -> dict[str, Any]:
    store = AtlasStore(ws)
    # Ensure atlas.db exists before checking the indexed read model.
    store.connect().close()
    issues: list[dict[str, Any]] = []

    if not source_spans_only:
        current_commit = current_git_commit(ws)
        for indexed in manifest_commits(ws):
            indexed_commit = indexed["indexed_commit"]
            if current_commit and indexed_commit and indexed_commit != current_commit:
                issues.append(
                    {
                        "type": "commit_mismatch",
                        "severity": "warning",
                        "repo_id": indexed["repo_id"],
                        "indexed_commit": indexed_commit,
                        "current_commit": current_commit,
                        "affected_fact_ids": [],
                        "message": f"Atlas manifest commit {indexed_commit} does not match current git commit {current_commit}",
                    }
                )

        dirty_files = current_dirty_files(ws)
        for path in sorted(dirty_files):
            issues.append(
                {
                    "type": "dirty_file",
                    "severity": "warning",
                    "path": path,
                    "affected_fact_ids": affected_fact_ids_for_paths(store, [path]),
                    "message": f"Git reports a dirty source file: {path}",
                }
            )

        with store.connect() as conn:
            evidence_rows = conn.execute("select fact_id, path from evidence where coalesce(path, '') != ''").fetchall()
        for ev in evidence_rows:
            evidence_path = ws.source_root / ev["path"]
            if not evidence_path.exists():
                issues.append(
                    {
                        "type": "missing_evidence_path",
                        "severity": "warning",
                        "path": ev["path"],
                        "affected_fact_ids": [ev["fact_id"]],
                        "message": f"Evidence path is missing: {ev['path']}",
                    }
                )

    with store.connect() as conn:
        span_rows = conn.execute("select span_id, path, start_line, end_line, content_hash from source_spans where coalesce(path, '') != ''").fetchall()
    for span in span_rows:
        expected = span["content_hash"] or ""
        path = ws.source_root / span["path"]
        if not path.exists():
            issues.append(
                {
                    "type": "missing_source_span_path",
                    "severity": "warning",
                    "path": span["path"],
                    "span_id": span["span_id"],
                    "affected_fact_ids": affected_fact_ids_for_span(store, span["span_id"], span["path"]),
                    "message": f"Source span path is missing: {span['path']}",
                }
            )
            continue
        if not valid_sha256(expected):
            continue
        actual_hashes = file_hash_candidates(path, span["start_line"], span["end_line"])
        if expected not in actual_hashes:
            issues.append(
                {
                    "type": "source_span_hash_mismatch",
                    "severity": "warning",
                    "path": span["path"],
                    "span_id": span["span_id"],
                    "expected_hash": expected,
                    "actual_hashes": sorted(actual_hashes),
                    "affected_fact_ids": affected_fact_ids_for_span(store, span["span_id"], span["path"]),
                    "message": f"Source span hash mismatch for {span['span_id']} at {span['path']}",
                }
            )

    affected = sorted({fact_id for issue in issues for fact_id in issue.get("affected_fact_ids", [])})
    return {
        "status": "clean" if not issues else "drift",
        "issue_count": len(issues),
        "affected_fact_ids": affected,
        "issues": issues,
    }


def print_drift_report(report: dict[str, Any]) -> None:
    if report["status"] == "clean":
        print("Atlas drift: clean")
        return
    print(f"Atlas drift: {report['issue_count']} issue(s)")
    for issue in report["issues"]:
        affected = issue.get("affected_fact_ids") or []
        suffix = f" affected_facts={','.join(affected)}" if affected else ""
        print(f"WARNING {issue['type']}: {issue['message']}{suffix}")


def cmd_drift(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    report = evaluate_drift(ws)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_drift_report(report)
    if args.strict and report["issue_count"]:
        raise SystemExit(7)


def cmd_verify_source_spans(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    report = evaluate_drift(ws, source_spans_only=True)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_drift_report(report)
    if args.strict and report["issue_count"]:
        raise SystemExit(7)


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


def pr_changed_files(ws: Workspace, pr: str) -> tuple[set[str], list[str]]:
    """Best-effort PR changed-file resolver.

    Supports GitHub PR URLs when the `gh` CLI is available. If PR metadata cannot
    be fetched in the current environment, callers still get a capability gap and
    can fall back to local git diff/status.
    """
    gaps: list[str] = []
    if not pr:
        return set(), gaps
    if pr.startswith("http") and "github.com" in pr:
        try:
            proc = subprocess.run(["gh", "pr", "diff", pr, "--name-only"], cwd=ws.source_root, text=True, capture_output=True)
        except OSError:
            gaps.append("PR link provided but gh CLI is not available to resolve changed files")
            return set(), gaps
        if proc.returncode == 0:
            return {line.strip() for line in proc.stdout.splitlines() if line.strip()}, gaps
        gaps.append(f"PR link provided but changed files could not be resolved: {proc.stderr.strip() or proc.stdout.strip()}")
    else:
        path = Path(pr)
        if path.exists():
            return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}, gaps
        gaps.append("PR argument is not a supported GitHub URL or changed-file list")
    return set(), gaps


def review_changed_files(ws: Workspace, pr: str = "") -> tuple[list[str], list[str]]:
    files = set(all_git_changed_files(ws))
    pr_files, gaps = pr_changed_files(ws, pr)
    files.update(pr_files)
    return sorted(files), gaps


def build_review(ws: Workspace, *, pr: str = "", no_agent: bool = False, strict: bool = False, limit: int = 30) -> dict[str, Any]:
    changed_files, gaps = review_changed_files(ws, pr)
    target = " ".join(changed_files) if changed_files else (pr or "changed files")
    impact = compute_impact(ws, target=target if not changed_files else None, changed=not bool(pr))
    if changed_files:
        # Ensure PR-resolved files participate even when they did not come from local git.
        impact = compute_impact(ws, target=" ".join(changed_files), changed=False)
        impact["changed_files"] = changed_files
    test_plan = select_tests_from_impact(ws, impact)
    test_plan["plan"] = {"commands": [test["test_id"] for test in test_plan["selected_tests"]], "notes": "Selected by deterministic Atlas impact analysis for review."}
    drift = evaluate_drift(ws)
    review_task = "Review changed files: " + (", ".join(changed_files) if changed_files else target)
    context_path = build_context(ws, "review", review_task, limit=limit)
    findings = []
    for fact in impact.get("facts", []):
        fact_id = fact.get("fact_id")
        if fact_id:
            findings.append({"severity": "info", "message": f"Review impacted Atlas fact [{fact_id}]: {fact.get('claim', '')}", "fact_ids": [fact_id]})
    report: dict[str, Any] = {
        "status": "pass" if drift.get("status") == "clean" else "warn",
        "changed_files": changed_files,
        "capability_gaps": gaps,
        "drift": drift,
        "impact": impact,
        "test_plan": test_plan,
        "context_pack": str(context_path),
        "findings": findings,
        "audit": None,
    }
    write_text(context_path.parent / "review-report.json", json.dumps(report, indent=2))
    with (context_path).open("a", encoding="utf-8") as f:
        f.write("\n## Review impact summary\n\n")
        f.write(json.dumps({"changed_files": changed_files, "findings": findings, "test_plan": test_plan["plan"], "drift_status": drift.get("status")}, indent=2))
        f.write("\n")
    if not no_agent:
        out_path = run_kiro(ws, context_path)
        report["kiro_output"] = str(out_path)
        report["audit"] = audit_answer(ws, out_path)
        write_text(context_path.parent / "review-report.json", json.dumps(report, indent=2))
    if strict and (report["drift"].get("issue_count") or (report.get("audit") and report["audit"].get("status") != "passed")):
        report["status"] = "fail"
    return report


def print_review_report(report: dict[str, Any]) -> None:
    print(f"Review status: {report['status']}")
    print(f"Context pack: {report['context_pack']}")
    print("Changed files:")
    for path in report.get("changed_files") or []:
        print(f"- {path}")
    if report.get("capability_gaps"):
        print("Capability gaps:")
        for gap in report["capability_gaps"]:
            print(f"- {gap}")
    print(f"Drift: {report['drift'].get('status')} ({report['drift'].get('issue_count')} issue(s))")
    if report.get("findings"):
        print("Findings:")
        for finding in report["findings"]:
            facts = ",".join(finding.get("fact_ids", []))
            print(f"- {finding['message']} facts={facts}")
    print("Test plan:")
    for command in report.get("test_plan", {}).get("plan", {}).get("commands", []):
        print(f"- {command}")


def cmd_review(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    report = build_review(ws, pr=args.pr or "", no_agent=args.no_agent, strict=args.strict, limit=args.limit)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_review_report(report)
    if args.strict and report.get("status") == "fail":
        raise SystemExit(8)


def artifact_rows(ws: Workspace, names: Iterable[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    wanted = {name.lower() for name in names}
    for root in [ws.atlas, ws.atlas / "contracts", ws.atlas / "indexes"]:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            lower = path.name.lower()
            if not any(name in lower for name in wanted):
                continue
            try:
                if path.suffix == ".jsonl":
                    content: Any = read_jsonl(path)
                else:
                    content = load_yaml_or_json(path) if path.suffix in {".json", ".yaml", ".yml"} else path.read_text(encoding="utf-8", errors="replace")
            except (OSError, json.JSONDecodeError, yaml.YAMLError):
                continue
            rows.append({"path": path.relative_to(ws.atlas).as_posix(), "content": content})
    return rows


def fact_ids_for_contract_query(ws: Workspace, query: str) -> list[str]:
    return [row["fact_id"] for row in AtlasStore(ws).search_facts(query, limit=10)]


def contract_check(ws: Workspace, kind: str) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    gaps: list[str] = []
    if kind in {"check", "api-ui"}:
        openapi = artifact_rows(ws, ["openapi"])
        clients = artifact_rows(ws, ["api_client_calls", "api-client", "client_calls"])
        hooks = artifact_rows(ws, ["query_hooks", "query-hooks"])
        if not openapi:
            gaps.append("openapi.json artifact is missing")
        if not clients:
            gaps.append("TypeScript api_client_calls/client artifact is missing")
        if not hooks:
            gaps.append("query_hooks artifact is missing")
        status = "pass" if openapi and (clients or hooks) else "warn"
        checks.append({
            "check": "api-ui",
            "status": status,
            "evidence": [row["path"] for row in [*openapi, *clients, *hooks]],
            "affected_facts": fact_ids_for_contract_query(ws, "api ui hook client route endpoint"),
            "suggested_fixes": [] if status == "pass" else ["Generate Atlas openapi.json plus TypeScript client/query hook artifacts before enforcing API/UI contract checks."],
        })
    if kind in {"check", "data"}:
        models = artifact_rows(ws, ["pydantic", "model"])
        fields = artifact_rows(ws, ["opensearch", "index", "field"])
        if not models:
            gaps.append("pydantic model artifact is missing")
        if not fields:
            gaps.append("opensearch index/field artifact is missing")
        status = "pass" if models and fields else "warn"
        checks.append({
            "check": "data",
            "status": status,
            "evidence": [row["path"] for row in [*models, *fields]],
            "affected_facts": fact_ids_for_contract_query(ws, "data model service field opensearch"),
            "suggested_fixes": [] if status == "pass" else ["Generate Atlas pydantic model and OpenSearch index/field artifacts before enforcing data contract checks."],
        })
    overall = "fail" if any(c["status"] == "fail" for c in checks) else "warn" if gaps or any(c["status"] == "warn" for c in checks) else "pass"
    return {"status": overall, "checks": checks, "capability_gaps": sorted(set(gaps))}


def print_contract_report(report: dict[str, Any]) -> None:
    print(f"Contract status: {report['status']}")
    for check in report.get("checks", []):
        print(f"- {check['check']}: {check['status']}")
        for ev in check.get("evidence", []):
            print(f"  evidence: {ev}")
        for fact_id in check.get("affected_facts", []):
            print(f"  fact: {fact_id}")
        for fix in check.get("suggested_fixes", []):
            print(f"  fix: {fix}")
    if report.get("capability_gaps"):
        print("Capability gaps:")
        for gap in report["capability_gaps"]:
            print(f"- {gap}")


def cmd_contract(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    report = contract_check(ws, args.contract_cmd)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_contract_report(report)


def eval_dirs(ws: Workspace) -> list[Path]:
    return [ws.atlas / "evals", ws.ngk / "evals"]


def default_eval_rows() -> list[dict[str, Any]]:
    return [
        {
            "id": "property_search_endpoint",
            "query": "What endpoint powers property search?",
            "must_retrieve": ["fact.api.property_search.endpoint"],
            "must_cite": ["fact.api.property_search.endpoint"],
            "must_not_claim": ["GraphQL"],
            "expected_trace": "trace.property_search.ui_to_api",
            "expected_tests": [],
        }
    ]


def read_eval_rows(ws: Workspace) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for directory in eval_dirs(ws):
        path = directory / "golden.jsonl"
        if path.exists():
            rows.extend(read_jsonl(path))
    return rows


def write_eval_row(ws: Workspace, row: dict[str, Any]) -> Path:
    path = ws.ngk / "evals" / "golden.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def run_eval(ws: Workspace, *, agent: bool = False, limit: int = 10) -> dict[str, Any]:
    rows = read_eval_rows(ws)
    results: list[dict[str, Any]] = []
    for row in rows:
        query = str(row.get("query") or row.get("task") or "")
        hits = AtlasStore(ws).search(query, limit=limit)
        retrieved_facts = sorted({hit.get("fact_id") for hit in hits if hit.get("fact_id")})
        context_path = build_context(ws, "eval", query, limit=limit)
        context_text = read_text(context_path)
        trace_ids = {trace.get("trace_id") for trace in json.loads(read_text(context_path.parent / "context-pack.json")).get("traces", [])}
        related_tests = set(json.loads(read_text(context_path.parent / "context-pack.json")).get("related_tests", []))
        failures: list[str] = []
        for fact_id in as_list(row.get("must_retrieve")):
            if fact_id not in retrieved_facts and fact_id not in context_text:
                failures.append(f"must_retrieve missing {fact_id}")
        for fact_id in as_list(row.get("must_cite")):
            if fact_id not in context_text:
                failures.append(f"must_cite missing from context {fact_id}")
        for text in as_list(row.get("must_not_claim")):
            if text and str(text) in context_text:
                failures.append(f"must_not_claim appeared in context {text}")
        expected_trace = row.get("expected_trace")
        if expected_trace and expected_trace not in trace_ids and str(expected_trace) not in context_text:
            failures.append(f"expected_trace missing {expected_trace}")
        for test in as_list(row.get("expected_tests")):
            if test not in related_tests and str(test) not in context_text:
                failures.append(f"expected_tests missing {test}")
        audit = None
        if agent:
            out_path = run_kiro(ws, context_path)
            audit = audit_answer(ws, out_path)
            for fact_id in as_list(row.get("must_cite")):
                if fact_id not in audit.get("resolved_fact_ids", []):
                    failures.append(f"agent did not cite {fact_id}")
        results.append({"id": row.get("id") or query, "status": "pass" if not failures else "fail", "failures": failures, "retrieved_facts": retrieved_facts, "context_pack": str(context_path), "audit": audit})
    return {"status": "pass" if all(r["status"] == "pass" for r in results) else "fail", "count": len(results), "results": results}


def print_eval_report(report: dict[str, Any]) -> None:
    print(f"Eval status: {report['status']} ({report['count']} case(s))")
    for result in report.get("results", []):
        print(f"- {result['id']}: {result['status']}")
        for failure in result.get("failures", []):
            print(f"  failure: {failure}")


def cmd_eval_init(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    path = ws.ngk / "evals" / "golden.jsonl"
    if not path.exists() or args.force:
        write_jsonl(path, default_eval_rows())
    print(path)


def cmd_eval_add(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    row = {
        "id": args.id,
        "query": " ".join(args.query),
        "must_retrieve": args.must_retrieve or [],
        "must_cite": args.must_cite or [],
        "must_not_claim": args.must_not_claim or [],
        "expected_trace": args.expected_trace or "",
        "expected_tests": args.expected_tests or [],
    }
    path = write_eval_row(ws, row)
    print(path)


def cmd_eval_run(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    report = run_eval(ws, agent=args.agent, limit=args.limit)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_eval_report(report)
    if args.strict and report["status"] != "pass":
        raise SystemExit(9)

def cmd_atlas_index(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    counts = AtlasIndexer(ws).index()
    print(json.dumps(counts, indent=2) if args.json else f"Indexed {counts}")


def cmd_sources(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    rows = AtlasStore(ws).search(" ".join(args.query), limit=args.limit)
    if args.json:
        print(json.dumps(rows, indent=2))
        return
    for i, row in enumerate(rows, 1):
        label = row.get("fact_id") or row.get("trace_id") or row["item_id"]
        print(f"[{i}] {label}  {row['item_type']}")
        print(f"    {row['title']}")
        if row.get("text"):
            print(f"    {row['text'][:220]}")
        if row.get("path"):
            print(f"    Path: {row['path']}")


def fact_payload(store: AtlasStore, fact_id: str) -> dict[str, Any]:
    fact = store.get_fact(fact_id)
    if not fact:
        raise SystemExit(f"Unknown fact: {fact_id}")
    evidence = []
    for ev in store.get_evidence(fact_id):
        row = dict(ev)
        span = store.get_source_span(ev["span_id"])
        if span:
            row["source_span"] = dict(span)
        evidence.append(row)
    return {"fact": dict(fact), "evidence": evidence, "related_traces": store.related_traces(fact_id), "related_tests": store.related_tests(fact_id)}


def cmd_fact_show(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    store = AtlasStore(ws)
    payload = fact_payload(store, args.fact_id)
    fact = payload["fact"]
    if args.json:
        print(json.dumps(payload, indent=2))
        return
    print(f"{fact['fact_id']}  {fact['confidence']}")
    print(f"Claim: {fact['claim']}")
    print(f"Atlas file: {fact['atlas_file']}")
    print(f"Atlas pointer: {fact['atlas_pointer']}")
    print("Source evidence:")
    for ev in payload["evidence"]:
        loc = ev["path"] or ev["pointer"] or ev["span_id"] or "unknown"
        if ev["start_line"] and ev["end_line"]:
            loc += f":{ev['start_line']}-{ev['end_line']}"
        print(f"- {loc} ({ev['method'] or 'unknown_method'})")
    if payload["related_traces"]:
        print("Related traces:")
        for trace in payload["related_traces"]:
            print(f"- {trace['trace_id']}: {trace['title']}")
    if payload["related_tests"]:
        print("Related tests:")
        for test in payload["related_tests"]:
            print(f"- {test}")


def cmd_fact_yaml(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    fact = AtlasStore(ws).get_fact(args.fact_id)
    if not fact:
        raise SystemExit(f"Unknown fact: {args.fact_id}")
    raw = json.loads(fact["raw_json"] or "{}")
    print(yaml.safe_dump(raw, sort_keys=False, allow_unicode=True))


def cmd_fact_code(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    evs = AtlasStore(ws).get_evidence(args.fact_id)
    if not evs:
        raise SystemExit(f"Unknown fact or no source evidence: {args.fact_id}")
    emitted = False
    for ev in evs:
        if not ev["path"] or not ev["start_line"] or not ev["end_line"]:
            continue
        path = ws.source_root / ev["path"]
        print(f"--- {ev['path']}:{ev['start_line']}-{ev['end_line']} ---")
        emitted = True
        if path.exists():
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            for lineno in range(int(ev["start_line"]), min(int(ev["end_line"]), len(lines)) + 1):
                print(f"{lineno:5}  {lines[lineno - 1]}")
        else:
            print("missing file")
    if not emitted:
        print(f"No line-addressable source evidence for {args.fact_id}")




def print_graph_neighbors(report: dict[str, Any]) -> None:
    print(f"Matched: {report['matched_target']['node_id']} ({report['matched_target']['match_type']})")
    print(f"Direction: {report['direction']}")
    if not report["neighbors"]:
        print("No neighbors found")
        return
    for item in report["neighbors"]:
        edge = item["edge"]
        print(f"- {item['node_id']} via {edge.get('edge_id')} ({edge.get('type') or 'unknown'}) confidence={edge.get('confidence') or 'unknown'}")


def print_graph_path(report: dict[str, Any]) -> None:
    print(f"From: {report['from']['node_id']}")
    print(f"To: {report['to']['node_id']}")
    if not report["found"]:
        print("No bounded path found")
        return
    print("Path:")
    for index, node in enumerate(report["nodes"], 1):
        print(f"{index}. {node['node_id']}")
    if report["edges"]:
        print("Edges:")
        for edge in report["edges"]:
            print(f"- {edge.get('from_id')} -> {edge.get('to_id')} ({edge.get('type') or 'unknown'}) confidence={edge.get('confidence') or 'unknown'}")


def print_trace_report(report: dict[str, Any]) -> None:
    matched = report["matched_target"]
    print(f"Matched target: {matched.get('target')} ({matched.get('match_type')})")
    trace = report.get("trace") or {}
    if trace:
        print(f"Trace: {trace.get('trace_id')} - {trace.get('title')}")
    print(f"Confidence: {report.get('confidence', 'unknown')}")
    print("Graph path:")
    path = report.get("graph_path") or {}
    if path.get("nodes"):
        print(" -> ".join(node["node_id"] for node in path["nodes"]))
    else:
        print("No graph path found")
    if report.get("related_facts"):
        print("Related facts:")
        for fact in report["related_facts"]:
            print(f"- {fact['fact_id']}: {fact['claim']}")
    if report.get("evidence_files"):
        print("Evidence files:")
        for path in report["evidence_files"]:
            print(f"- {path}")
    if report.get("related_tests"):
        print("Related tests:")
        for test in report["related_tests"]:
            print(f"- {test}")


def cmd_trace(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    report = AtlasStore(ws).trace_report(args.target)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_trace_report(report)


def cmd_graph_neighbors(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    report = AtlasStore(ws).graph_neighbors(args.target, reverse=args.reverse)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_graph_neighbors(report)


def cmd_graph_path(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    report = AtlasStore(ws).graph_path(args.source, args.target, max_depth=args.max_depth)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_graph_path(report)


def print_impact_report(report: dict[str, Any]) -> None:
    label = report.get("target") or ("changed files" if report.get("changed") else "workspace")
    print(f"Impact analysis: {label}")
    if report.get("changed_files"):
        print("Changed files:")
        for path in report["changed_files"]:
            print(f"- {path}")
    for section, key in (("Impacted facts", "facts"), ("Impacted traces", "traces"), ("Impacted nodes", "nodes")):
        rows = report.get(key) or []
        if not rows:
            continue
        print(f"{section}:")
        for row in rows:
            item_id = row.get("fact_id") or row.get("trace_id") or row.get("node_id") or row.get("path")
            reasons = "; ".join(row.get("reasons") or [])
            print(f"- {item_id} confidence={row.get('confidence', 'unknown')} reason={reasons}")


def print_test_selection(report: dict[str, Any]) -> None:
    tests = report.get("selected_tests") or []
    print(f"Selected tests: {len(tests)}")
    for test in tests:
        print(f"- {test['test_id']} confidence={test.get('confidence', 'unknown')}")
        for reason in test.get("reasons") or []:
            print(f"  reason: {reason}")
    gaps = report.get("coverage_gaps") or {}
    if gaps.get("facts") or gaps.get("traces"):
        print("Coverage gaps:")
        for fact_id in gaps.get("facts") or []:
            print(f"- fact without related tests: {fact_id}")
        for trace_id in gaps.get("traces") or []:
            print(f"- trace without related tests: {trace_id}")


def cmd_impact(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    report = compute_impact(ws, target=args.target, changed=args.changed)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_impact_report(report)


def cmd_test_select(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    impact = compute_impact(ws, target=args.target, changed=args.changed)
    report = select_tests_from_impact(ws, impact)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_test_selection(report)


def cmd_test_plan(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    impact = compute_impact(ws, target=args.target, changed=args.changed)
    report = select_tests_from_impact(ws, impact)
    report["plan"] = {
        "commands": [test["test_id"] for test in report["selected_tests"]],
        "notes": "Selected by deterministic Atlas impact analysis; review coverage gaps before relying on the plan.",
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_test_selection(report)

def cmd_ctx_build(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    path = build_context(ws, args.mode, " ".join(args.request), limit=args.limit)
    print(path)



def cmd_ctx_explain(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    session_dir = resolve_session(ws, args.session)
    explain_path = session_dir / "selection-explain.json"
    if not explain_path.exists():
        raise SystemExit(f"No context selection explanation in {session_dir}")
    payload = json.loads(read_text(explain_path))
    if args.json:
        print(json.dumps(payload, indent=2))
        return
    print(f"Context selection explanation: {payload.get('session_id', session_dir.name)}")
    print("Facts:")
    for fact in payload.get("facts", []):
        print(f"- {fact.get('fact_id')}: {fact.get('reason')}")
    print("Traces:")
    for trace in payload.get("traces", []):
        reasons = "; ".join(trace.get("reasons") or [])
        print(f"- {trace.get('trace_id')}: {reasons}")
    gaps = payload.get("known_gaps") or {}
    if gaps:
        print("Known gaps:")
        for key, value in gaps.items():
            print(f"- {key}: {json.dumps(value, ensure_ascii=False)}")

def cmd_ask(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    path = build_context(ws, "ask", " ".join(args.question), limit=args.limit)
    print(f"Context pack: {path}")
    if not args.no_agent:
        out = run_kiro(ws, path)
        print(f"Kiro output: {out}")
        print(f"Audit: {out.parent / 'audit.json'}")


def cmd_verify(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    session_dir = resolve_session(ws, args.session)
    answer = session_dir / "kiro-output.raw.md"
    if not answer.exists():
        raise SystemExit(f"No Kiro answer in {session_dir}")
    audit = audit_answer(ws, answer)
    print(json.dumps(audit, indent=2) if args.json else f"Audit {audit['status']}: resolved={len(audit['resolved_fact_ids'])} missing={len(audit['missing_fact_ids'])} unsupported={len(audit['unsupported_claims'])}")
    if args.strict and audit["status"] != "passed":
        raise SystemExit(6)


def cmd_smart(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    session_dir = resolve_session(ws, args.session)
    print(f"ngk smart MVP session: {session_dir.name}")
    audit = session_dir / "audit.json"
    if audit.exists():
        print(read_text(audit))
    answer = session_dir / "kiro-output.raw.md"
    if answer.exists():
        print("\n--- Answer ---")
        print(read_text(answer))
    citations = session_dir / "citations.json"
    if citations.exists():
        print("\n--- Citations ---")
        parsed = json.loads(read_text(citations))
        for fact_id in parsed.get("fact_ids", []):
            print(f"- {fact_id}")


def add_workspace_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--atlas", default=argparse.SUPPRESS)
    parser.add_argument("--ngk-dir", default=argparse.SUPPRESS)


def add_fact_command(sub: argparse._SubParsersAction[argparse.ArgumentParser], name: str, func: Any, *, json_flag: bool = False) -> None:
    s = sub.add_parser(name)
    add_workspace_args(s)
    s.add_argument("fact_id")
    if json_flag:
        s.add_argument("--json", action="store_true")
    s.set_defaults(func=func)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Atlas-native ngk")
    p.set_defaults(atlas=".atlas", ngk_dir=".ngk")
    add_workspace_args(p)
    sub = p.add_subparsers(dest="cmd", required=True)

    atlas = sub.add_parser("atlas")
    add_workspace_args(atlas)
    atlas_sub = atlas.add_subparsers(dest="atlas_cmd", required=True)
    s = atlas_sub.add_parser("index")
    add_workspace_args(s)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_atlas_index)

    s = sub.add_parser("atlas-index")
    add_workspace_args(s)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_atlas_index)

    s = sub.add_parser("sources")
    add_workspace_args(s)
    s.add_argument("query", nargs="+")
    s.add_argument("--limit", type=int, default=20)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_sources)

    s = sub.add_parser("drift")
    add_workspace_args(s)
    s.add_argument("--json", action="store_true")
    s.add_argument("--strict", action="store_true")
    s.set_defaults(func=cmd_drift)

    s = sub.add_parser("verify-source-spans")
    add_workspace_args(s)
    s.add_argument("--json", action="store_true")
    s.add_argument("--strict", action="store_true")
    s.set_defaults(func=cmd_verify_source_spans)

    s = sub.add_parser("impact")
    add_workspace_args(s)
    s.add_argument("target", nargs="?")
    s.add_argument("--changed", action="store_true")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_impact)

    s = sub.add_parser("review")
    add_workspace_args(s)
    s.add_argument("--pr", default="")
    s.add_argument("--limit", type=int, default=30)
    s.add_argument("--no-agent", action="store_true")
    s.add_argument("--strict", action="store_true")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_review)

    contract = sub.add_parser("contract")
    add_workspace_args(contract)
    contract_sub = contract.add_subparsers(dest="contract_cmd", required=True)
    for name in ("check", "api-ui", "data"):
        s = contract_sub.add_parser(name)
        add_workspace_args(s)
        s.add_argument("--json", action="store_true")
        s.set_defaults(func=cmd_contract)

    eval_p = sub.add_parser("eval")
    add_workspace_args(eval_p)
    eval_sub = eval_p.add_subparsers(dest="eval_cmd", required=True)
    s = eval_sub.add_parser("init")
    add_workspace_args(s)
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_eval_init)
    s = eval_sub.add_parser("run")
    add_workspace_args(s)
    s.add_argument("--agent", action="store_true")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--json", action="store_true")
    s.add_argument("--strict", action="store_true")
    s.set_defaults(func=cmd_eval_run)
    s = eval_sub.add_parser("add")
    add_workspace_args(s)
    s.add_argument("id")
    s.add_argument("query", nargs="+")
    s.add_argument("--must-retrieve", action="append")
    s.add_argument("--must-cite", action="append")
    s.add_argument("--must-not-claim", action="append")
    s.add_argument("--expected-trace")
    s.add_argument("--expected-tests", action="append")
    s.set_defaults(func=cmd_eval_add)

    s = sub.add_parser("test-select")
    add_workspace_args(s)
    s.add_argument("target", nargs="?")
    s.add_argument("--changed", action="store_true")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_test_select)

    s = sub.add_parser("test-plan")
    add_workspace_args(s)
    s.add_argument("target", nargs="?")
    s.add_argument("--changed", action="store_true")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_test_plan)

    s = sub.add_parser("trace")
    add_workspace_args(s)
    s.add_argument("target")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_trace)

    graph = sub.add_parser("graph")
    add_workspace_args(graph)
    graph_sub = graph.add_subparsers(dest="graph_cmd", required=True)
    s = graph_sub.add_parser("neighbors")
    add_workspace_args(s)
    s.add_argument("target")
    s.add_argument("--reverse", action="store_true")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_graph_neighbors)
    s = graph_sub.add_parser("path")
    add_workspace_args(s)
    s.add_argument("source")
    s.add_argument("target")
    s.add_argument("--max-depth", type=int, default=6)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_graph_path)

    fact = sub.add_parser("fact")
    add_workspace_args(fact)
    fact_sub = fact.add_subparsers(dest="fact_cmd", required=True)
    add_fact_command(fact_sub, "show", cmd_fact_show, json_flag=True)
    add_fact_command(fact_sub, "yaml", cmd_fact_yaml)
    add_fact_command(fact_sub, "code", cmd_fact_code)

    add_fact_command(sub, "fact-show", cmd_fact_show, json_flag=True)
    add_fact_command(sub, "fact-yaml", cmd_fact_yaml)
    add_fact_command(sub, "fact-code", cmd_fact_code)

    ctx = sub.add_parser("ctx")
    add_workspace_args(ctx)
    ctx_sub = ctx.add_subparsers(dest="ctx_cmd", required=True)
    s = ctx_sub.add_parser("build")
    add_workspace_args(s)
    s.add_argument("mode", choices=["ask", "review", "debug", "plan"])
    s.add_argument("request", nargs="+")
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(func=cmd_ctx_build)
    s = ctx_sub.add_parser("explain")
    add_workspace_args(s)
    s.add_argument("session", nargs="?", default="latest")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_ctx_explain)

    s = sub.add_parser("ctx-build")
    add_workspace_args(s)
    s.add_argument("mode", choices=["ask", "review", "debug", "plan"])
    s.add_argument("request", nargs="+")
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(func=cmd_ctx_build)

    s = sub.add_parser("ask")
    add_workspace_args(s)
    s.add_argument("question", nargs="+")
    s.add_argument("--limit", type=int, default=30)
    s.add_argument("--no-agent", action="store_true")
    s.set_defaults(func=cmd_ask)

    s = sub.add_parser("verify-answer")
    add_workspace_args(s)
    s.add_argument("session", nargs="?", default="latest")
    s.add_argument("--json", action="store_true")
    s.add_argument("--strict", action="store_true")
    s.set_defaults(func=cmd_verify)

    s = sub.add_parser("smart")
    add_workspace_args(s)
    s.add_argument("--session", default="latest")
    s.set_defaults(func=cmd_smart)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
