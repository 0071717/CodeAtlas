from __future__ import annotations

from typing import Any


def _finding_key(f: dict[str, Any]) -> tuple:
    return (tuple(sorted(f.get("fact_ids") or [])), tuple(sorted(f.get("risk_tags") or [])), str(f.get("claim", "")).lower()[:80])


def detect_conflicts(results: list[dict[str, Any]]) -> dict[str, Any]:
    conflicts=[]; duplicates=[]; seen={}
    findings=[]
    for result in results:
        for f in result.get("findings", []) or []:
            findings.append((result.get("agent_profile"), f))
            key=_finding_key(f)
            if key in seen:
                duplicates.append({"type":"duplicate","finding_ids":[seen[key].get("finding_id"), f.get("finding_id")],"fact_ids":f.get("fact_ids",[])})
            else:
                seen[key]=f
    for i,(pa,a) in enumerate(findings):
        for pb,b in findings[i+1:]:
            ca=str(a.get("claim","")).lower(); cb=str(b.get("claim","")).lower()
            shared=set(a.get("fact_ids") or []) & set(b.get("fact_ids") or [])
            if ("no impact" in ca and b.get("support") == "supported") or ("no impact" in cb and a.get("support") == "supported"):
                conflicts.append({"type":"contradiction","profiles":[pa,pb],"finding_ids":[a.get("finding_id"),b.get("finding_id")],"reason":"no-impact vs supported issue"})
            elif shared and a.get("support") == "contradicted" or b.get("support") == "contradicted":
                conflicts.append({"type":"contradiction","profiles":[pa,pb],"finding_ids":[a.get("finding_id"),b.get("finding_id")],"reason":"contradicted support label overlaps facts"})
            elif shared and a.get("confidence") != b.get("confidence"):
                conflicts.append({"type":"confidence_mismatch","profiles":[pa,pb],"finding_ids":[a.get("finding_id"),b.get("finding_id")],"fact_ids":sorted(shared)})
    return {"schema_version":"1","duplicates":duplicates,"conflicts":conflicts,"status":"conflict" if conflicts else "ok"}
