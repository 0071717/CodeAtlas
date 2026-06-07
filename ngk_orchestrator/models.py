from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

RESULT_BLOCK_RE = re.compile(r"<ngk_agent_result>\s*(.*?)\s*</ngk_agent_result>", re.S)
VALID_STATUS = {"completed", "failed", "partial"}
VALID_VERDICT = {"no_issues", "issues_found", "needs_followup", "blocked"}
VALID_CONFIDENCE = {"high", "medium", "low"}
VALID_SUPPORT = {"supported", "inferred", "not_confirmed", "contradicted", "out_of_scope"}
VALID_SEVERITY = {"critical", "high", "medium", "low", "info"}
CONF_RANK = {"low": 1, "medium": 2, "high": 3, "unknown": 0}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def orchestration_id() -> str:
    return datetime.now(timezone.utc).strftime("orch-%Y%m%dT%H%M%SZ")


def task_id(profile: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "-", profile).strip("-") or "task"
    return f"task-{safe}-{datetime.now(timezone.utc).strftime('%H%M%S%f')}"


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any, *, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=indent, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def read_yaml(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_agent_result(text: str) -> tuple[dict[str, Any] | None, list[str]]:
    match = RESULT_BLOCK_RE.search(text or "")
    if not match:
        return None, ["missing <ngk_agent_result> block"]
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        return None, [f"invalid agent result JSON: {exc}"]
    if not isinstance(payload, dict):
        return None, ["agent result block must contain a JSON object"]
    return payload, []


def validate_agent_result(payload: dict[str, Any]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    for key in ("schema_version", "task_id", "agent_profile", "status", "verdict", "confidence", "summary", "findings", "uncertainties", "not_confirmed", "requested_followups"):
        if key not in payload:
            errors.append(f"missing required field: {key}")
    if payload.get("schema_version") != "1":
        errors.append("schema_version must be '1'")
    if payload.get("status") not in VALID_STATUS:
        errors.append("status must be completed|failed|partial")
    if payload.get("verdict") not in VALID_VERDICT:
        errors.append("verdict must be no_issues|issues_found|needs_followup|blocked")
    if payload.get("confidence") not in VALID_CONFIDENCE:
        errors.append("confidence must be high|medium|low")
    findings = payload.get("findings")
    if not isinstance(findings, list):
        errors.append("findings must be a list")
        findings = []
    for idx, finding in enumerate(findings):
        if not isinstance(finding, dict):
            errors.append(f"findings[{idx}] must be an object")
            continue
        for key in ("finding_id", "severity", "title", "claim", "support", "confidence", "fact_ids", "evidence", "recommended_tests", "risk_tags"):
            if key not in finding:
                errors.append(f"findings[{idx}] missing required field: {key}")
        if finding.get("severity") not in VALID_SEVERITY:
            errors.append(f"findings[{idx}].severity invalid")
        if finding.get("support") not in VALID_SUPPORT:
            errors.append(f"findings[{idx}].support invalid")
        if finding.get("confidence") not in VALID_CONFIDENCE:
            errors.append(f"findings[{idx}].confidence invalid")
        for list_key in ("fact_ids", "evidence", "recommended_tests", "risk_tags"):
            if list_key in finding and not isinstance(finding.get(list_key), list):
                errors.append(f"findings[{idx}].{list_key} must be a list")
        if finding.get("support") == "supported" and not finding.get("fact_ids"):
            errors.append(f"findings[{idx}] supported finding requires at least one fact_id")
        if finding.get("support") == "inferred" and not (finding.get("reason") or finding.get("evidence")):
            errors.append(f"findings[{idx}] inferred finding requires reason or evidence")
    for key in ("uncertainties", "not_confirmed", "requested_followups"):
        if key in payload and not isinstance(payload.get(key), list):
            errors.append(f"{key} must be a list")
    return ValidationResult(not errors, errors, warnings)


def base_agent_result(task_id_value: str, profile: str, **updates: Any) -> dict[str, Any]:
    payload = {
        "schema_version": "1",
        "task_id": task_id_value,
        "agent_profile": profile,
        "status": "completed",
        "verdict": "no_issues",
        "confidence": "medium",
        "summary": "No issues were reported by this deterministic placeholder result.",
        "findings": [],
        "uncertainties": [],
        "not_confirmed": [],
        "requested_followups": [],
    }
    payload.update(updates)
    return payload
