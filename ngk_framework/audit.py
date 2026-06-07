from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import CITATION_BLOCK_RE, FACT_ID_RE, INLINE_FACT_ID_RE, Workspace, as_list, clean_fact_id, compact_json, read_text, write_text
from .store import AtlasStore
from .drift import evaluate_drift

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



def audit_answer(ws: Workspace, answer_path: Path) -> dict[str, Any]:
    return AuditEngine(ws).audit_file(answer_path)
