from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ngk_framework.base import Workspace

from ngk_orchestrator.profiles_api import PROMPT_DIR, RULE_DIR, list_profiles, validate_profiles

DENIED_COMMANDS = [
    "ngk orchestrate .*",
    "ngk delegate .*",
    "git commit .*",
    "git push .*",
    "rm -rf .*",
    "npm install .*",
    "pnpm install .*",
    "yarn add .*",
    "pip install .*",
    "poetry add .*",
    "kiro .*",
    ".*--trust-all-tools.*",
]
ALLOWED_COMMANDS = [
    "ngk tool sources .*",
    "ngk tool fact .*",
    "ngk tool trace .*",
    "ngk tool impact .*",
    "ngk tool tests .*",
    "ngk tool contract check .*",
    "ngk tool contract boundary .*",
    "ngk tool drift .*",
    "ngk tool verify-result .*",
    "ngk tool context .*",
]
RULE_FILES = [
    "shared.md",
    "citation-rules.md",
    "output-contract.md",
    "support-taxonomy.md",
    "prompt-injection-boundary.md",
    "read-only-rules.md",
]


def render_prompt(profile: dict[str, Any]) -> str:
    prompt_path = PROMPT_DIR / profile["prompt_template"]
    prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else f"You are {profile['id']}."
    shared = "\n\n".join((RULE_DIR / name).read_text(encoding="utf-8") for name in RULE_FILES if (RULE_DIR / name).exists())
    scope = json.dumps(profile.get("scope", {}), indent=2, sort_keys=True)
    return (
        f"# ngk agent: {profile['id']}\n\n"
        f"## Scope\n```json\n{scope}\n```\n\n"
        f"{prompt}\n\n{shared}\n\n"
        "Return a single <ngk_agent_result> JSON block matching schema version 1."
    )


def generated_agent(profile: dict[str, Any]) -> dict[str, Any]:
    allowed_builtin = profile.get("tools", {}).get("allowed_builtin") or ["read", "grep"]
    # Shell is exposed only for restricted ngk tool commands; hooks provide an additional guardrail.
    if "shell" not in allowed_builtin:
        allowed_builtin = list(allowed_builtin) + ["shell"]
    return {
        "name": f"ngk-{profile['id']}",
        "description": profile.get("description", ""),
        "prompt": render_prompt(profile),
        "tools": ["read", "grep", "shell"],
        "allowedTools": allowed_builtin,
        "resources": [f"file://../../ngk_orchestrator/agent_rules/{name}" for name in RULE_FILES],
        "includeMcpJson": False,
        "hooks": {
            "agentSpawn": [{"command": "python3 .ngk/kiro-hooks/agent_spawn_context.py"}],
            "userPromptSubmit": [{"command": "python3 .ngk/kiro-hooks/user_prompt_context.py"}],
            "preToolUse": [{"matcher": "*", "command": "python3 .ngk/kiro-hooks/pre_tool_guard.py"}],
            "postToolUse": [{"matcher": "*", "command": "python3 .ngk/kiro-hooks/post_tool_audit.py"}],
            "stop": [{"command": "python3 .ngk/kiro-hooks/stop_verify_agent_result.py"}],
        },
        "toolsSettings": {
            "shell": {
                "allowedCommands": ALLOWED_COMMANDS,
                "deniedCommands": DENIED_COMMANDS,
                "autoAllowReadonly": True,
            }
        },
        "metadata": {
            "canonical_profile": profile["id"],
            "mcp_disabled": True,
            "generated_by": "ngk agents generate-kiro",
        },
        "welcomeMessage": f"ngk {profile['id']} active. Read-only Atlas-cited findings only.",
    }


def generate_kiro_agents(ws: Workspace) -> dict[str, Any]:
    validation = validate_profiles()
    if validation["status"] != "ok":
        return {"status": "error", "validation": validation, "generated": []}
    out_dir = ws.root / ".kiro" / "agents"
    out_dir.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []
    for profile in list_profiles():
        payload = generated_agent(profile)
        path = out_dir / f"ngk-{profile['id']}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        generated.append(str(path))
    return {"status": "ok", "generated": generated, "count": len(generated)}
