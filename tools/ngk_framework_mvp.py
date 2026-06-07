#!/usr/bin/env python3
"""MVP Atlas-native ngk framework.

This single-file implementation is a bridge for Codex. It indexes Atlas facts,
builds a small SQLite read model, creates Kiro context packs, parses Atlas fact
citations, audits answers, and provides basic source/fact inspection.

It is dependency-light. PyYAML is used when available; JSON fact files still work
without it. Codex should split this into package modules as described in
`docs/CODEX_ATLAS_NGK_ENGINE_HANDOFF.md`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

FACT_ID_RE = re.compile(r"\bfact\.[A-Za-z0-9_.:/-]+")
CITATION_BLOCK_RE = re.compile(r"<atlas_citations>\s*(.*?)\s*</atlas_citations>", re.S)


def now_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def load_yaml_or_json(path: Path) -> Any:
    text = read_text(path)
    if path.suffix.lower() == ".json":
        return json.loads(text)
    if yaml is not None:
        return yaml.safe_load(text) or {}
    try:
        return json.loads(text)
    except Exception as exc:
        raise RuntimeError(f"Cannot parse {path}; install PyYAML for YAML support") from exc


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
            """
        )

    def iter_fact_files(self) -> Iterable[Path]:
        facts_dir = self.ws.atlas / "facts"
        if not facts_dir.exists():
            return []
        return sorted([p for p in facts_dir.rglob("*") if p.suffix.lower() in {".yaml", ".yml", ".json"}])

    def normalize_evidence(self, fact_id: str, item: dict[str, Any], index: int) -> Evidence:
        lines = item.get("lines") or item.get("line_range") or []
        start_line = end_line = None
        if isinstance(lines, list) and len(lines) >= 2:
            start_line, end_line = int(lines[0]), int(lines[1])
        return Evidence(
            evidence_id=item.get("evidence_id") or f"evidence.{fact_id}.{index}",
            fact_id=fact_id,
            path=item.get("path") or item.get("file") or "",
            start_line=start_line,
            end_line=end_line,
            pointer=item.get("pointer") or "",
            method=item.get("method") or item.get("extracted_by") or "",
            span_id=item.get("span_id") or "",
            repo_id=item.get("repo_id") or item.get("repo") or "",
        )

    def load_facts(self) -> tuple[list[Fact], list[Evidence]]:
        facts: list[Fact] = []
        evidence: list[Evidence] = []
        for path in self.iter_fact_files():
            data = load_yaml_or_json(path)
            fact_rows = data.get("facts", []) if isinstance(data, dict) else []
            for idx, row in enumerate(fact_rows):
                if not isinstance(row, dict):
                    continue
                fact_id = row.get("id") or row.get("fact_id")
                if not fact_id:
                    continue
                subject = row.get("subject") or {}
                subject_id = subject.get("id") if isinstance(subject, dict) else ""
                pointer = row.get("atlas_pointer") or f"{path.as_posix()}#/facts/{idx}"
                facts.append(
                    Fact(
                        fact_id=fact_id,
                        claim=row.get("claim") or row.get("summary") or "",
                        type=row.get("type") or "unknown",
                        confidence=row.get("confidence") or "unknown",
                        atlas_file=path.as_posix(),
                        atlas_pointer=pointer,
                        subject_id=subject_id or "",
                        raw=row,
                    )
                )
                for eidx, item in enumerate(row.get("evidence") or []):
                    if isinstance(item, dict):
                        evidence.append(self.normalize_evidence(fact_id, item, eidx))
        return facts, evidence

    def load_source_spans(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for path in [self.ws.atlas / "indexes" / "source_spans.jsonl", self.ws.atlas / "source_spans.jsonl"]:
            rows.extend(read_jsonl(path))
        return rows

    def load_traces(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        traces_dir = self.ws.atlas / "traces"
        if traces_dir.exists():
            for p in sorted(traces_dir.rglob("*.jsonl")):
                rows.extend(read_jsonl(p))
            for p in sorted(traces_dir.rglob("*.json")):
                data = load_yaml_or_json(p)
                if isinstance(data, list):
                    rows.extend([x for x in data if isinstance(x, dict)])
                elif isinstance(data, dict):
                    rows.extend(data.get("traces", []))
        return rows

    def index(self) -> dict[str, int]:
        facts, evidence = self.load_facts()
        spans = self.load_source_spans()
        traces = self.load_traces()
        with self.connect() as conn:
            self.reset_schema(conn)
            conn.executemany(
                "insert into facts values (?,?,?,?,?,?,?,?)",
                [(f.fact_id, f.claim, f.type, f.confidence, f.atlas_file, f.atlas_pointer, f.subject_id, json.dumps(f.raw or {}, ensure_ascii=False)) for f in facts],
            )
            conn.executemany(
                "insert into evidence values (?,?,?,?,?,?,?,?,?)",
                [(e.evidence_id, e.fact_id, e.repo_id, e.path, e.start_line, e.end_line, e.pointer, e.method, e.span_id) for e in evidence],
            )
            conn.executemany(
                "insert into source_spans values (?,?,?,?,?,?,?,?,?)",
                [(s.get("span_id"), s.get("repo_id", ""), s.get("file_id", ""), s.get("path", ""), s.get("language", ""), s.get("start_line"), s.get("end_line"), s.get("content_hash", ""), json.dumps(s, ensure_ascii=False)) for s in spans if s.get("span_id")],
            )
            conn.executemany(
                "insert into traces values (?,?,?,?,?)",
                [(t.get("trace_id"), t.get("title", ""), t.get("summary", ""), t.get("confidence", ""), json.dumps(t, ensure_ascii=False)) for t in traces if t.get("trace_id")],
            )
        self.write_indexes(facts, evidence)
        return {"facts": len(facts), "evidence": len(evidence), "spans": len(spans), "traces": len(traces)}

    def write_indexes(self, facts: list[Fact], evidence: list[Evidence]) -> None:
        ev_by_fact: dict[str, list[Evidence]] = {}
        for e in evidence:
            ev_by_fact.setdefault(e.fact_id, []).append(e)
        citation_rows = []
        source_cards = []
        retrieval = []
        for f in facts:
            evs = ev_by_fact.get(f.fact_id, [])
            citation_rows.append({**asdict(f), "evidence": [asdict(e) for e in evs]})
            source_cards.append({"card_id": f"source_card.{f.fact_id}", "fact_id": f.fact_id, "title": f.fact_id, "claim": f.claim, "confidence": f.confidence, "atlas_source": f.atlas_pointer, "evidence_sources": [asdict(e) for e in evs]})
            retrieval.append({"item_id": f.fact_id, "item_type": "fact", "title": f.fact_id, "text": " ".join([f.fact_id, f.type, f.claim, " ".join(e.path for e in evs)]), "priority": 1.0 if f.confidence == "high" else 0.5})
        write_jsonl(self.ws.cache / "citation_index.jsonl", citation_rows)
        write_jsonl(self.ws.cache / "source_cards.jsonl", source_cards)
        write_jsonl(self.ws.cache / "retrieval_index.jsonl", retrieval)


class AtlasStore:
    def __init__(self, ws: Workspace) -> None:
        self.ws = ws

    def connect(self) -> sqlite3.Connection:
        if not self.ws.db.exists():
            AtlasIndexer(self.ws).index()
        conn = sqlite3.connect(self.ws.db)
        conn.row_factory = sqlite3.Row
        return conn

    def search_facts(self, query: str, limit: int = 20) -> list[sqlite3.Row]:
        terms = [t.lower() for t in re.findall(r"[A-Za-z0-9_./:-]+", query)]
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


def parse_citations(text: str) -> dict[str, Any]:
    block = CITATION_BLOCK_RE.search(text)
    if block:
        try:
            payload = json.loads(block.group(1))
            fact_ids = sorted({c.get("fact_id") for c in payload.get("citations", []) if c.get("fact_id")})
            if not fact_ids:
                fact_ids = sorted(set(FACT_ID_RE.findall(text)))
            return {"format": "atlas_citations", "fact_ids": fact_ids, "payload": payload}
        except json.JSONDecodeError:
            pass
    return {"format": "inline", "fact_ids": sorted(set(FACT_ID_RE.findall(text))), "payload": {}}


def build_context(ws: Workspace, mode: str, request: str, limit: int = 30) -> Path:
    store = AtlasStore(ws)
    facts = store.search_facts(request, limit=limit)
    session_id = f"{now_id()}-{mode}"
    session_dir = ws.sessions / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    selected = []
    lines = [
        "# ngk / Atlas context pack",
        "",
        f"Mode: {mode}",
        "",
        "## User request",
        "",
        request,
        "",
        "## Agent rules",
        "",
        "Use only the Atlas facts and evidence below for architectural/API/UI/data/model/test claims.",
        "Every such claim must cite Atlas fact IDs.",
        "If Atlas does not confirm a claim, write: Not confirmed by Atlas.",
        "End with a machine-readable <atlas_citations> JSON block.",
        "",
        "## Retrieved facts",
        "",
    ]
    for row in facts:
        evs = store.get_evidence(row["fact_id"])
        selected.append(dict(row))
        lines.extend([f"### {row['fact_id']}", "", f"Claim: {row['claim']}", f"Confidence: {row['confidence']}", f"Atlas source: {row['atlas_pointer']}", "Evidence:"])
        for ev in evs:
            loc = ev["path"] or ev["pointer"] or ev["span_id"] or "unknown"
            if ev["start_line"] and ev["end_line"]:
                loc += f":{ev['start_line']}-{ev['end_line']}"
            lines.append(f"- {loc} ({ev['method'] or 'unknown_method'})")
        lines.append("")
    lines.extend([
        "## Required output block",
        "",
        "```text",
        "<atlas_citations>",
        '{"claims":[{"claim_id":"claim.1","text":"...","support":"supported","fact_ids":["fact.example"]}],"citations":[{"fact_id":"fact.example","used_for_claims":["claim.1"]}],"not_confirmed":[]}',
        "</atlas_citations>",
        "```",
    ])
    write_text(session_dir / "context-pack.md", "\n".join(lines) + "\n")
    write_text(session_dir / "context-pack.json", json.dumps({"mode": mode, "request": request, "facts": selected}, indent=2))
    write_jsonl(session_dir / "selected-facts.jsonl", selected)
    write_text(session_dir / "session.json", json.dumps({"session_id": session_id, "mode": mode, "request": request, "created_at": now_id()}, indent=2))
    write_text(ws.sessions / "latest", session_id)
    return session_dir / "context-pack.md"


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
    text = read_text(answer_path)
    parsed = parse_citations(text)
    store = AtlasStore(ws)
    resolved = []
    missing = []
    for fact_id in parsed["fact_ids"]:
        fact = store.get_fact(fact_id)
        if fact:
            resolved.append(fact_id)
        else:
            missing.append(fact_id)
    status = "passed" if not missing else "failed"
    audit = {"status": status, "resolved_fact_ids": resolved, "missing_fact_ids": missing, "citation_format": parsed["format"]}
    write_text(answer_path.parent / "audit.json", json.dumps(audit, indent=2))
    return audit


def cmd_atlas_index(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    counts = AtlasIndexer(ws).index()
    print(json.dumps(counts, indent=2) if args.json else f"Indexed {counts}")


def cmd_sources(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    rows = AtlasStore(ws).search_facts(" ".join(args.query), limit=args.limit)
    if args.json:
        print(json.dumps([dict(r) for r in rows], indent=2))
        return
    for i, row in enumerate(rows, 1):
        print(f"[{i}] {row['fact_id']}  {row['confidence']}")
        print(f"    {row['claim']}")
        print(f"    Atlas: {row['atlas_pointer']}")


def cmd_fact_show(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    store = AtlasStore(ws)
    fact = store.get_fact(args.fact_id)
    if not fact:
        raise SystemExit(f"Unknown fact: {args.fact_id}")
    evs = store.get_evidence(args.fact_id)
    if args.json:
        print(json.dumps({"fact": dict(fact), "evidence": [dict(e) for e in evs]}, indent=2))
        return
    print(f"{fact['fact_id']}  {fact['confidence']}")
    print(fact["claim"])
    print(f"Atlas: {fact['atlas_pointer']}")
    print("Evidence:")
    for ev in evs:
        loc = ev["path"] or ev["pointer"] or ev["span_id"] or "unknown"
        if ev["start_line"] and ev["end_line"]:
            loc += f":{ev['start_line']}-{ev['end_line']}"
        print(f"- {loc} ({ev['method'] or 'unknown_method'})")


def cmd_fact_code(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    evs = AtlasStore(ws).get_evidence(args.fact_id)
    for ev in evs:
        if not ev["path"] or not ev["start_line"] or not ev["end_line"]:
            continue
        path = ws.root / ev["path"]
        print(f"--- {ev['path']}:{ev['start_line']}-{ev['end_line']} ---")
        if path.exists():
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            for lineno in range(int(ev["start_line"]), min(int(ev["end_line"]), len(lines)) + 1):
                print(f"{lineno:5}  {lines[lineno - 1]}")
        else:
            print("missing file")


def cmd_ctx_build(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    path = build_context(ws, args.mode, " ".join(args.request), limit=args.limit)
    print(path)


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
    print(json.dumps(audit, indent=2) if args.json else f"Audit {audit['status']}: resolved={len(audit['resolved_fact_ids'])} missing={len(audit['missing_fact_ids'])}")
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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Atlas-native ngk MVP")
    p.add_argument("--atlas", default=".atlas")
    p.add_argument("--ngk-dir", default=".ngk")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("atlas-index")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_atlas_index)

    s = sub.add_parser("sources")
    s.add_argument("query", nargs="+")
    s.add_argument("--limit", type=int, default=20)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_sources)

    s = sub.add_parser("fact-show")
    s.add_argument("fact_id")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_fact_show)

    s = sub.add_parser("fact-code")
    s.add_argument("fact_id")
    s.set_defaults(func=cmd_fact_code)

    s = sub.add_parser("ctx-build")
    s.add_argument("mode", choices=["ask", "review", "debug", "plan"])
    s.add_argument("request", nargs="+")
    s.add_argument("--limit", type=int, default=30)
    s.set_defaults(func=cmd_ctx_build)

    s = sub.add_parser("ask")
    s.add_argument("question", nargs="+")
    s.add_argument("--limit", type=int, default=30)
    s.add_argument("--no-agent", action="store_true")
    s.set_defaults(func=cmd_ask)

    s = sub.add_parser("verify-answer")
    s.add_argument("session", nargs="?", default="latest")
    s.add_argument("--json", action="store_true")
    s.add_argument("--strict", action="store_true")
    s.set_defaults(func=cmd_verify)

    s = sub.add_parser("smart")
    s.add_argument("--session", default="latest")
    s.set_defaults(func=cmd_smart)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
