from __future__ import annotations

from typing import Any

from ngk_framework.base import Workspace
from ngk_framework.drift import evaluate_drift
from ngk_framework.store import AtlasStore

from ngk_orchestrator.models import CONF_RANK, validate_agent_result


def verify_agent_result(ws: Workspace, payload: dict[str, Any], *, strict: bool = False, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    schema = validate_agent_result(payload)
    errors = list(schema.errors)
    warnings = list(schema.warnings)
    store = AtlasStore(ws)
    drift = evaluate_drift(ws)
    stale_ids = {fid for issue in drift.get("issues", []) for fid in issue.get("affected_fact_ids", [])}
    audited_findings=[]
    domains = set((profile or {}).get("scope", {}).get("domains", []))
    for finding in payload.get("findings", []) if isinstance(payload.get("findings"), list) else []:
        audit={"finding_id":finding.get("finding_id"),"accepted":False,"errors":[],"warnings":[]}
        if finding.get("support") == "not_confirmed":
            audit["errors"].append("not_confirmed findings are never accepted")
        if finding.get("support") == "inferred" and not (finding.get("reason") or finding.get("evidence")):
            audit["errors"].append("inferred findings require reason")
        if finding.get("support") == "supported":
            for fid in finding.get("fact_ids") or []:
                fact = store.get_fact(fid)
                if not fact:
                    audit["errors"].append(f"nonexistent fact_id: {fid}")
                    continue
                ev = store.get_evidence(fid)
                if not ev and str(fact.get("confidence") or "") not in {"low", "summary-only"}:
                    audit["errors"].append(f"fact has no evidence: {fid}")
                if fid in stale_ids:
                    msg=f"stale fact_id: {fid}"
                    (audit["errors"] if strict else audit["warnings"]).append(msg)
                if CONF_RANK.get(finding.get("confidence"),0) > CONF_RANK.get(str(fact.get("confidence") or "unknown"),0) and str(fact.get("confidence") or "") in {"low","medium"}:
                    audit["warnings"].append(f"finding confidence exceeds fact confidence: {fid}")
        if domains and "all" not in domains:
            tags=set(finding.get("risk_tags") or [])
            if tags and not (tags & domains):
                audit["warnings"].append("finding may be out of profile scope")
        audit["accepted"] = not audit["errors"] and finding.get("support") == "supported"
        audited_findings.append(audit)
        errors.extend(audit["errors"])
        warnings.extend(audit["warnings"])
    status = "passed" if not errors and (not strict or not warnings) else "failed"
    return {"schema_version":"1","status":status,"valid_schema":schema.valid,"errors":errors,"warnings":warnings,"audited_findings":audited_findings,"strict":strict}
