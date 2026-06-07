from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

PROFILE_IDS = [
    "impact-analyzer", "frontend-impact-reviewer", "api-contract-reviewer", "cross-stack-contract-reviewer", "data-impact-reviewer", "test-gap-reviewer", "security-reviewer", "critic", "synthesis",
]

PROFILE_DIR = Path(__file__).parent / "profiles"
PROMPT_DIR = Path(__file__).parent / "prompts"
RULE_DIR = Path(__file__).parent / "agent_rules"


def load_profile(profile_id: str) -> dict[str, Any]:
    path = PROFILE_DIR / f"{profile_id}.yaml"
    if not path.exists():
        raise SystemExit(f"Unknown profile: {profile_id}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    payload["_path"] = str(path)
    return payload


def list_profiles() -> list[dict[str, Any]]:
    return [load_profile(pid) for pid in PROFILE_IDS if (PROFILE_DIR / f"{pid}.yaml").exists()]


def validate_profile(payload: dict[str, Any]) -> list[str]:
    errors = []
    for key in ("id", "description", "mode", "scope", "tools", "output_contract", "prompt_template"):
        if key not in payload:
            errors.append(f"missing {key}")
    if payload.get("mode") not in {"read_only", "patch_proposal", "write"}:
        errors.append("mode invalid")
    if not (PROMPT_DIR / str(payload.get("prompt_template", ""))).exists():
        errors.append("prompt_template missing")
    return errors


def validate_profiles() -> dict[str, Any]:
    rows=[]; ok=True
    for profile in list_profiles():
        errors=validate_profile(profile)
        rows.append({"id":profile.get("id"),"valid":not errors,"errors":errors})
        ok = ok and not errors
    return {"status":"ok" if ok else "error","profiles":rows}
