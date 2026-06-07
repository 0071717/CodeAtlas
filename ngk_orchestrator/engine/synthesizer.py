from __future__ import annotations

from pathlib import Path
from typing import Any

from ngk_orchestrator.models import write_json
from .conflict_detector import detect_conflicts


def synthesize(results: list[dict[str, Any]], audits: list[dict[str, Any]], *, out_dir: Path | None = None) -> dict[str, Any]:
    conflicts=detect_conflicts(results)
    rejected=[]; accepted=[]; unknowns=[]; tests=[]
    audit_by_idx = audits
    conflicted_ids={fid for c in conflicts.get("conflicts",[]) for fid in c.get("finding_ids",[])}
    for idx,result in enumerate(results):
        audit=audit_by_idx[idx] if idx < len(audit_by_idx) else {}
        accepted_ids={x.get("finding_id") for x in audit.get("audited_findings",[]) if x.get("accepted")}
        for f in result.get("findings",[]) or []:
            if f.get("finding_id") in accepted_ids and f.get("finding_id") not in conflicted_ids:
                accepted.append(f)
                for t in f.get("recommended_tests") or []:
                    tests.append({"test":t,"reason":f.get("finding_id")})
            else:
                rejected.append({"finding":f,"reason":"not audited accepted, unsupported, stale, out-of-scope, duplicate, or contradicted"})
        unknowns.extend(result.get("uncertainties",[]) or [])
        unknowns.extend(result.get("not_confirmed",[]) or [])
    verdict = "needs_followup" if conflicts.get("conflicts") or unknowns else ("issues_found" if accepted else "safe")
    payload={"schema_version":"1","verdict":verdict,"accepted_findings":accepted,"rejected_findings":rejected,"conflicts":conflicts.get("conflicts",[]),"duplicates":conflicts.get("duplicates",[]),"known_unknowns":unknowns,"recommended_tests":tests,"audit":{"result_count":len(results),"accepted_count":len(accepted),"rejected_count":len(rejected)}}
    if out_dir:
        write_json(out_dir/"conflicts.json", conflicts)
        write_json(out_dir/"synthesis.json", payload)
        lines=["# Orchestration Summary","",f"Overall verdict: {verdict}","","## Accepted findings",*(f"- {f.get('finding_id')}: {f.get('title')}" for f in accepted),"","## Conflicts",*(f"- {c.get('type')}: {c.get('reason')}" for c in payload['conflicts']),"","## Known unknowns",*(f"- {u}" for u in unknowns),"","## Rejected findings",*(f"- {r['finding'].get('finding_id')}: {r['reason']}" for r in rejected),"","## Recommended tests",*(f"- {t['test']} ({t['reason']})" for t in tests),"","## Audit",f"Accepted: {len(accepted)} Rejected: {len(rejected)}"]
        (out_dir/"summary.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return payload
