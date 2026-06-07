from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .audit import audit_answer
from .base import Workspace, as_list, read_jsonl, read_text, write_jsonl
from .context import build_context, run_kiro
from .store import AtlasStore

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

