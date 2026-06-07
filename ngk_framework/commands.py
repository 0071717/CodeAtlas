#!/usr/bin/env python3
"""Atlas-native ngk command-line interface."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from .audit import audit_answer, parse_citations
from .base import Workspace, file_hash_candidates, read_text
from .context import build_context, resolve_session, run_kiro
from .contract import cmd_contract
from .drift import cmd_drift, cmd_verify_source_spans
from .evals import cmd_eval_add, cmd_eval_init, cmd_eval_run
from .impact import compute_impact, select_tests_from_impact
from .indexer import AtlasIndexer
from .review import cmd_review
from .store import AtlasStore

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
