from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .audit import audit_answer, parse_citations
from .base import Workspace, as_list, compact_json, now_id, read_text, write_jsonl, write_text
from .drift import evaluate_drift
from .impact import row_raw
from .store import AtlasStore

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
