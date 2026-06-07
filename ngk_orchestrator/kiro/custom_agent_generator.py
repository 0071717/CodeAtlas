from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ngk_framework.base import Workspace

from ngk_orchestrator.profiles_api import PROMPT_DIR, RULE_DIR, list_profiles, validate_profiles

DENIED = ["ngk orchestrate", "ngk delegate", "git commit", "git push", "rm ", "rm -rf", "npm install", "pip install", "--trust-all-tools"]
ALLOWED = [
    "ngk tool sources", "ngk tool fact", "ngk tool trace", "ngk tool impact", "ngk tool tests", "ngk tool contract check", "ngk tool contract boundary", "ngk tool drift", "ngk tool verify-result", "ngk tool context",
]


def render_prompt(profile: dict[str, Any]) -> str:
    prompt = (PROMPT_DIR / profile["prompt_template"]).read_text(encoding="utf-8")
    shared = "\n\n".join((RULE_DIR / name).read_text(encoding="utf-8") for name in ["shared.md", "citation-rules.md", "output-contract.md", "support-taxonomy.md", "prompt-injection-boundary.md", "read-only-rules.md"])
    return f"# Agent scope: {profile['id']}\n\n{prompt}\n\n{shared}\n"


def generated_agent(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": f"ngk-{profile['id']}",
        "description": profile.get("description", ""),
        "prompt": render_prompt(profile),
        "tools": ["read", "grep", "shell"],
        "allowedTools": profile.get("tools", {}).get("allowed_builtin", ["read", "grep"]),
        "resources": [str((RULE_DIR / name).as_posix()) for name in ["shared.md", "citation-rules.md", "output-contract.md", "support-taxonomy.md", "prompt-injection-boundary.md", "read-only-rules.md"]],
        "includeMcpJson": False,
        "hooks": {"agentSpawn": ".ngk/kiro-hooks/agent_spawn_context.py", "preToolUse": ".ngk/kiro-hooks/pre_tool_guard.py", "postToolUse": ".ngk/kiro-hooks/post_tool_audit.py", "stop": ".ngk/kiro-hooks/stop_verify_agent_result.py"},
        "toolsSettings": {"shell": {"allowedCommands": ALLOWED, "deniedCommands": DENIED}},
        "metadata": {"canonical_profile": profile["id"], "mcp_disabled": True},
    }


def generate_kiro_agents(ws: Workspace) -> dict[str, Any]:
    validation = validate_profiles()
    if validation["status"] != "ok":
        return {"status": "error", "validation": validation, "generated": []}
    out_dir = ws.root / ".kiro" / "agents"
    out_dir.mkdir(parents=True, exist_ok=True)
    generated=[]
    for profile in list_profiles():
        payload = generated_agent(profile)
        path = out_dir / f"ngk-{profile['id']}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        generated.append(str(path))
    return {"status": "ok", "generated": generated}
