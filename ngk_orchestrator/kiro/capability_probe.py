from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml

from ngk_framework.base import Workspace

from ngk_orchestrator.models import utc_now, write_json

DEFAULT_KIRO_CONFIG = {
    "kiro": {
        "command": "kiro-cli",
        "chat_args": ["chat", "--no-interactive"],
        "default_trust_tools": "read,grep",
        "require_api_key": False,
        "agent_arg_style": "--agent {agent_name}",
        "timeout_seconds": 240,
    }
}


def load_kiro_config(ws: Workspace) -> dict[str, Any]:
    config = json.loads(json.dumps(DEFAULT_KIRO_CONFIG))
    for path in (ws.root / "ngk.yaml", ws.root / ".ngk.yaml", ws.ngk / "config.yaml"):
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(data.get("kiro"), dict):
                config["kiro"].update(data["kiro"])
    return config


def probe_kiro(ws: Workspace, *, env: dict[str, str] | None = None) -> dict[str, Any]:
    cfg = load_kiro_config(ws)["kiro"]
    command = str(cfg.get("command") or "kiro-cli")
    report: dict[str, Any] = {"schema_version": "1", "timestamp": utc_now(), "command": command, "configured": cfg, "available": False, "auth": "not_checked", "status": "warning", "warnings": [], "errors": []}
    if cfg.get("require_api_key") and not (env or os.environ).get("KIRO_API_KEY"):
        report["auth"] = "missing_api_key"
        report["errors"].append("KIRO_API_KEY is required by configuration but is not set")
        report["status"] = "error"
        write_json(ws.ngk / "kiro" / "capabilities.json", report)
        return report
    binary = shutil.which(command)
    if not binary:
        report["errors"].append(f"Kiro command not found: {command}")
        report["missing_binary"] = True
        write_json(ws.ngk / "kiro" / "capabilities.json", report)
        return report
    report["available"] = True
    try:
        proc = subprocess.run([binary, "--version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, env={**os.environ, **(env or {})})
    except subprocess.TimeoutExpired:
        report["warnings"].append("version probe timed out")
    else:
        report["version_stdout"] = proc.stdout.strip()
        report["version_stderr"] = proc.stderr.strip()
        report["version_exit_code"] = proc.returncode
        blob = (proc.stdout + proc.stderr).lower()
        if "auth" in blob or "unauthorized" in blob or "login" in blob:
            report["auth"] = "failed_or_required"
            report["status"] = "warning"
        else:
            report["auth"] = "not_required_or_available"
            report["status"] = "ok" if proc.returncode == 0 else "warning"
    write_json(ws.ngk / "kiro" / "capabilities.json", report)
    return report
