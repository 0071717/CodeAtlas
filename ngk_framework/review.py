from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .audit import audit_answer
from .base import Workspace, write_text
from .context import build_context, run_kiro
from .drift import evaluate_drift
from .impact import all_git_changed_files, compute_impact, select_tests_from_impact

def pr_changed_files(ws: Workspace, pr: str) -> tuple[set[str], list[str]]:
    """Best-effort PR changed-file resolver.

    Supports GitHub PR URLs when the `gh` CLI is available. If PR metadata cannot
    be fetched in the current environment, callers still get a capability gap and
    can fall back to local git diff/status.
    """
    gaps: list[str] = []
    if not pr:
        return set(), gaps
    if pr.startswith("http") and "github.com" in pr:
        try:
            proc = subprocess.run(["gh", "pr", "diff", pr, "--name-only"], cwd=ws.source_root, text=True, capture_output=True)
        except OSError:
            gaps.append("PR link provided but gh CLI is not available to resolve changed files")
            return set(), gaps
        if proc.returncode == 0:
            return {line.strip() for line in proc.stdout.splitlines() if line.strip()}, gaps
        gaps.append(f"PR link provided but changed files could not be resolved: {proc.stderr.strip() or proc.stdout.strip()}")
    else:
        path = Path(pr)
        if path.exists():
            return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}, gaps
        gaps.append("PR argument is not a supported GitHub URL or changed-file list")
    return set(), gaps


def review_changed_files(ws: Workspace, pr: str = "") -> tuple[list[str], list[str]]:
    files = set(all_git_changed_files(ws))
    pr_files, gaps = pr_changed_files(ws, pr)
    files.update(pr_files)
    return sorted(files), gaps


def build_review(ws: Workspace, *, pr: str = "", no_agent: bool = False, strict: bool = False, limit: int = 30) -> dict[str, Any]:
    changed_files, gaps = review_changed_files(ws, pr)
    target = " ".join(changed_files) if changed_files else (pr or "changed files")
    impact = compute_impact(ws, target=target if not changed_files else None, changed=not bool(pr))
    if changed_files:
        # Ensure PR-resolved files participate even when they did not come from local git.
        impact = compute_impact(ws, target=" ".join(changed_files), changed=False)
        impact["changed_files"] = changed_files
    test_plan = select_tests_from_impact(ws, impact)
    test_plan["plan"] = {"commands": [test["test_id"] for test in test_plan["selected_tests"]], "notes": "Selected by deterministic Atlas impact analysis for review."}
    drift = evaluate_drift(ws)
    review_task = "Review changed files: " + (", ".join(changed_files) if changed_files else target)
    context_path = build_context(ws, "review", review_task, limit=limit)
    findings = []
    for fact in impact.get("facts", []):
        fact_id = fact.get("fact_id")
        if fact_id:
            findings.append({"severity": "info", "message": f"Review impacted Atlas fact [{fact_id}]: {fact.get('claim', '')}", "fact_ids": [fact_id]})
    report: dict[str, Any] = {
        "status": "pass" if drift.get("status") == "clean" else "warn",
        "changed_files": changed_files,
        "capability_gaps": gaps,
        "drift": drift,
        "impact": impact,
        "test_plan": test_plan,
        "context_pack": str(context_path),
        "findings": findings,
        "audit": None,
    }
    write_text(context_path.parent / "review-report.json", json.dumps(report, indent=2))
    with (context_path).open("a", encoding="utf-8") as f:
        f.write("\n## Review impact summary\n\n")
        f.write(json.dumps({"changed_files": changed_files, "findings": findings, "test_plan": test_plan["plan"], "drift_status": drift.get("status")}, indent=2))
        f.write("\n")
    if not no_agent:
        out_path = run_kiro(ws, context_path)
        report["kiro_output"] = str(out_path)
        report["audit"] = audit_answer(ws, out_path)
        write_text(context_path.parent / "review-report.json", json.dumps(report, indent=2))
    if strict and (report["drift"].get("issue_count") or (report.get("audit") and report["audit"].get("status") != "passed")):
        report["status"] = "fail"
    return report


def print_review_report(report: dict[str, Any]) -> None:
    print(f"Review status: {report['status']}")
    print(f"Context pack: {report['context_pack']}")
    print("Changed files:")
    for path in report.get("changed_files") or []:
        print(f"- {path}")
    if report.get("capability_gaps"):
        print("Capability gaps:")
        for gap in report["capability_gaps"]:
            print(f"- {gap}")
    print(f"Drift: {report['drift'].get('status')} ({report['drift'].get('issue_count')} issue(s))")
    if report.get("findings"):
        print("Findings:")
        for finding in report["findings"]:
            facts = ",".join(finding.get("fact_ids", []))
            print(f"- {finding['message']} facts={facts}")
    print("Test plan:")
    for command in report.get("test_plan", {}).get("plan", {}).get("commands", []):
        print(f"- {command}")


def cmd_review(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    report = build_review(ws, pr=args.pr or "", no_agent=args.no_agent, strict=args.strict, limit=args.limit)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_review_report(report)
    if args.strict and report.get("status") == "fail":
        raise SystemExit(8)


