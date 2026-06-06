#!/usr/bin/env python3
"""CodeAtlas preflight doctor.

Runs offline sanity checks before transferring CodeAtlas into a restricted Kiro network.
This tool checks that the framework itself is coherent and ready for Kiro/ngk use.
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path.cwd()
ATLAS = ROOT / "atlas"

REQUIRED_FILES = [
    "README.md",
    "docs/CANONICAL_EXECUTION_PATH.md",
    "docs/LEGACY_AND_EXPERIMENTAL_PATHS.md",
    "docs/PRE_TRANSFER_READINESS_CHECKLIST.md",
    "docs/KIRO_ZIP_HANDOFF.md",
    "docs/FRAMEWORK_ARCHITECTURE_V2.md",
    "docs/LAYER_BUILD_CONTRACT.md",
    "docs/KIRO_FRAMEWORK_IMPLEMENTATION_GUIDE.md",
    "docs/NGK_TRACE_VISUAL_FLOW_EXPLORER.md",
    "docs/NGK_ECOSYSTEM_HARDENING_PLAN.md",
    "docs/TOOL_SUITE_V2.md",
    "docs/GRAPHIFY_PATTERNS_ADOPTED.md",
    "docs/REPO_CLEANUP_AUDIT.md",
    "atlas/config/project.yaml",
    "atlas/config/project.schema.json",
    "atlas/config/ecosystem-bindings.yaml",
    "atlas/tools/codeatlas_v2_suite.py",
    "atlas/tools/codeatlas_v2_canonical.py",
    "atlas/tools/ngk_trace_regraph_exporter.py",
    "atlas/tools/codeatlas_graph_report.py",
    "atlas/tools/codeatlas_graph_html.py",
    "atlas/tools/codeatlas_query.py",
    "atlas/tools/validate_artifacts.py",
    "atlas/scripts/run-framework-v2-suite.sh",
    "atlas/scripts/run-pre-transfer-check.sh",
    "atlas/scripts/README.md",
    "atlas/legacy/README.md",
    "atlas/legacy/scripts/README.md",
    "docs/legacy/README.md",
]

RECOMMENDED_FILES = [
    "docs/AI_ASSISTED_EXTRACTION_STRATEGY.md",
    "docs/REACT_STACK_MAPPING_GUIDE.md",
    "atlas/tools/react_stack_indexer.py",
]

LEGACY_FIRST_RUN_COMMANDS = [
    "bash atlas/scripts/run-auto.sh",
    "bash atlas/scripts/run-pilot-auto.sh",
    "bash atlas/scripts/run-foundation.sh",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def check_file(path: str, severity: str, findings: list[dict]) -> None:
    if not (ROOT / path).exists():
        findings.append({"severity": severity, "type": "missing_file", "path": path})


def check_no_required_b64(findings: list[dict]) -> None:
    tool = read(ATLAS / "tools" / "codeatlas_v2_suite.py")
    if "b64decode" in tool or "codeatlas_v2_suite_payload" in tool:
        findings.append({"severity": "error", "type": "encoded_launcher_detected", "path": "atlas/tools/codeatlas_v2_suite.py"})


def check_start_here(findings: list[dict]) -> None:
    text = read(ROOT / "docs" / "START_HERE_FOR_KIRO.md")
    if not text:
        findings.append({"severity": "warning", "type": "missing_start_here", "path": "docs/START_HERE_FOR_KIRO.md"})
        return
    if "docs/CANONICAL_EXECUTION_PATH.md" not in text:
        findings.append({"severity": "warning", "type": "start_here_missing_canonical_doc", "path": "docs/START_HERE_FOR_KIRO.md"})
    if "run-auto.sh" in text and "legacy" not in text.lower():
        findings.append({"severity": "warning", "type": "start_here_still_mentions_run_auto_without_legacy_warning", "path": "docs/START_HERE_FOR_KIRO.md"})


def check_project_config(findings: list[dict]) -> None:
    text = read(ATLAS / "config" / "project.yaml")
    if not text:
        findings.append({"severity": "error", "type": "missing_project_yaml", "path": "atlas/config/project.yaml"})
        return
    if "replace-me" in text or "../frontend-repo" in text or "../backend-repo" in text:
        findings.append({"severity": "warning", "type": "project_config_appears_template", "path": "atlas/config/project.yaml", "note": "Edit paths after transfer or before first real extraction."})
    if "repositories:" not in text:
        findings.append({"severity": "error", "type": "project_config_missing_repositories", "path": "atlas/config/project.yaml"})


def check_docs_consistency(findings: list[dict]) -> None:
    canonical = read(ROOT / "docs" / "CANONICAL_EXECUTION_PATH.md")
    runner = read(ATLAS / "tools" / "codeatlas_v2_canonical.py")
    if "V2 deterministic path is canonical" not in canonical:
        findings.append({"severity": "error", "type": "canonical_doc_missing_decision", "path": "docs/CANONICAL_EXECUTION_PATH.md"})
    if "graph-report" not in runner or "validate-artifacts" not in runner:
        findings.append({"severity": "warning", "type": "canonical_runner_missing_graphify_helpers", "path": "atlas/tools/codeatlas_v2_canonical.py"})
    legacy = read(ROOT / "docs" / "LEGACY_AND_EXPERIMENTAL_PATHS.md")
    for cmd in LEGACY_FIRST_RUN_COMMANDS:
        if cmd not in legacy:
            findings.append({"severity": "warning", "type": "legacy_doc_missing_command", "path": "docs/LEGACY_AND_EXPERIMENTAL_PATHS.md", "command": cmd})
    cleanup = read(ROOT / "docs" / "REPO_CLEANUP_AUDIT.md")
    if "atlas/legacy/scripts/run-auto.sh" not in cleanup:
        findings.append({"severity": "warning", "type": "cleanup_audit_missing_archived_legacy_scripts", "path": "docs/REPO_CLEANUP_AUDIT.md"})


def write_report(findings: list[dict]) -> None:
    report = {
        "generated_at": now(),
        "status": "ok" if not any(f["severity"] == "error" for f in findings) else "error",
        "finding_count": len(findings),
        "findings": findings,
    }
    path = ATLAS / "audit" / "preflight-doctor-report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


def main() -> int:
    findings: list[dict] = []
    for file in REQUIRED_FILES:
        check_file(file, "error", findings)
    for file in RECOMMENDED_FILES:
        check_file(file, "warning", findings)
    check_no_required_b64(findings)
    check_start_here(findings)
    check_project_config(findings)
    check_docs_consistency(findings)
    write_report(findings)
    return 1 if any(f["severity"] == "error" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
