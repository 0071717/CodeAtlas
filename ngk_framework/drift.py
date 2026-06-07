from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Iterable

from .base import Workspace, as_list, file_hash_candidates, read_text, valid_sha256
from .store import AtlasStore

def run_git(ws: Workspace, args: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(["git", "-C", str(ws.source_root), *args], text=True, capture_output=True)
    except OSError:
        return 127, ""
    return proc.returncode, proc.stdout.strip()


def current_git_commit(ws: Workspace) -> str:
    code, out = run_git(ws, ["rev-parse", "HEAD"])
    return out if code == 0 else ""


def current_dirty_files(ws: Workspace) -> set[str]:
    code, out = run_git(ws, ["status", "--porcelain=v1", "-z", "--untracked-files=no", "--", "."])
    if code != 0 or not out:
        return set()
    files: set[str] = set()
    parts = out.split("\0")
    i = 0
    while i < len(parts):
        entry = parts[i]
        i += 1
        if not entry:
            continue
        status = entry[:2]
        path = entry[2:].lstrip() if len(entry) > 2 else ""
        if status.startswith("R") or status.startswith("C"):
            if i < len(parts) and parts[i]:
                path = parts[i]
                i += 1
        if path:
            files.add(path)
    return files


def manifest_commits(ws: Workspace) -> list[dict[str, str]]:
    manifest_path = ws.atlas / "manifest.json"
    if not manifest_path.exists():
        return []
    try:
        data = json.loads(read_text(manifest_path))
    except (OSError, json.JSONDecodeError):
        return []
    commits: list[dict[str, str]] = []

    def add(repo_id: str, commit: Any) -> None:
        if commit:
            commits.append({"repo_id": str(repo_id or "default"), "indexed_commit": str(commit)})

    if isinstance(data, dict):
        for key in ("indexed_commit", "git_commit", "commit", "source_commit", "head_commit"):
            add(str(data.get("repo_id") or data.get("project") or "default"), data.get(key))
        indexed = data.get("indexed_commits") or data.get("commits")
        if isinstance(indexed, dict):
            for repo_id, commit in indexed.items():
                add(str(repo_id), commit)
        elif isinstance(indexed, list):
            for item in indexed:
                if isinstance(item, dict):
                    add(str(item.get("repo_id") or item.get("repo") or item.get("name") or "default"), item.get("commit") or item.get("indexed_commit") or item.get("git_commit"))
        for repo in as_list(data.get("repositories") or data.get("repos")):
            if isinstance(repo, dict):
                add(str(repo.get("repo_id") or repo.get("id") or repo.get("name") or "default"), repo.get("commit") or repo.get("indexed_commit") or repo.get("git_commit"))
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in commits:
        key = (row["repo_id"], row["indexed_commit"])
        if key not in seen:
            deduped.append(row)
            seen.add(key)
    return deduped


def affected_fact_ids_for_paths(store: AtlasStore, paths: Iterable[str]) -> list[str]:
    wanted = {p for p in paths if p}
    if not wanted:
        return []
    with store.connect() as conn:
        rows = conn.execute(
            """
            select distinct e.fact_id
            from evidence e
            left join source_spans s on s.span_id = e.span_id
            where e.path in ({}) or s.path in ({})
            """.format(",".join("?" for _ in wanted), ",".join("?" for _ in wanted)),
            [*wanted, *wanted],
        ).fetchall()
    return sorted(row["fact_id"] for row in rows)


def affected_fact_ids_for_span(store: AtlasStore, span_id: str, path: str) -> list[str]:
    with store.connect() as conn:
        rows = conn.execute(
            "select distinct fact_id from evidence where span_id=? or path=?",
            (span_id, path),
        ).fetchall()
    return sorted(row["fact_id"] for row in rows)


def evaluate_drift(ws: Workspace, *, source_spans_only: bool = False) -> dict[str, Any]:
    store = AtlasStore(ws)
    # Ensure atlas.db exists before checking the indexed read model.
    store.connect().close()
    issues: list[dict[str, Any]] = []

    if not source_spans_only:
        current_commit = current_git_commit(ws)
        for indexed in manifest_commits(ws):
            indexed_commit = indexed["indexed_commit"]
            if current_commit and indexed_commit and indexed_commit != current_commit:
                issues.append(
                    {
                        "type": "commit_mismatch",
                        "severity": "warning",
                        "repo_id": indexed["repo_id"],
                        "indexed_commit": indexed_commit,
                        "current_commit": current_commit,
                        "affected_fact_ids": [],
                        "message": f"Atlas manifest commit {indexed_commit} does not match current git commit {current_commit}",
                    }
                )

        dirty_files = current_dirty_files(ws)
        for path in sorted(dirty_files):
            issues.append(
                {
                    "type": "dirty_file",
                    "severity": "warning",
                    "path": path,
                    "affected_fact_ids": affected_fact_ids_for_paths(store, [path]),
                    "message": f"Git reports a dirty source file: {path}",
                }
            )

        with store.connect() as conn:
            evidence_rows = conn.execute("select fact_id, path from evidence where coalesce(path, '') != ''").fetchall()
        for ev in evidence_rows:
            evidence_path = ws.source_root / ev["path"]
            if not evidence_path.exists():
                issues.append(
                    {
                        "type": "missing_evidence_path",
                        "severity": "warning",
                        "path": ev["path"],
                        "affected_fact_ids": [ev["fact_id"]],
                        "message": f"Evidence path is missing: {ev['path']}",
                    }
                )

    with store.connect() as conn:
        span_rows = conn.execute("select span_id, path, start_line, end_line, content_hash from source_spans where coalesce(path, '') != ''").fetchall()
    for span in span_rows:
        expected = span["content_hash"] or ""
        path = ws.source_root / span["path"]
        if not path.exists():
            issues.append(
                {
                    "type": "missing_source_span_path",
                    "severity": "warning",
                    "path": span["path"],
                    "span_id": span["span_id"],
                    "affected_fact_ids": affected_fact_ids_for_span(store, span["span_id"], span["path"]),
                    "message": f"Source span path is missing: {span['path']}",
                }
            )
            continue
        if not valid_sha256(expected):
            continue
        actual_hashes = file_hash_candidates(path, span["start_line"], span["end_line"])
        if expected not in actual_hashes:
            issues.append(
                {
                    "type": "source_span_hash_mismatch",
                    "severity": "warning",
                    "path": span["path"],
                    "span_id": span["span_id"],
                    "expected_hash": expected,
                    "actual_hashes": sorted(actual_hashes),
                    "affected_fact_ids": affected_fact_ids_for_span(store, span["span_id"], span["path"]),
                    "message": f"Source span hash mismatch for {span['span_id']} at {span['path']}",
                }
            )

    affected = sorted({fact_id for issue in issues for fact_id in issue.get("affected_fact_ids", [])})
    return {
        "status": "clean" if not issues else "drift",
        "issue_count": len(issues),
        "affected_fact_ids": affected,
        "issues": issues,
    }


def print_drift_report(report: dict[str, Any]) -> None:
    if report["status"] == "clean":
        print("Atlas drift: clean")
        return
    print(f"Atlas drift: {report['issue_count']} issue(s)")
    for issue in report["issues"]:
        affected = issue.get("affected_fact_ids") or []
        suffix = f" affected_facts={','.join(affected)}" if affected else ""
        print(f"WARNING {issue['type']}: {issue['message']}{suffix}")


def cmd_drift(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    report = evaluate_drift(ws)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_drift_report(report)
    if args.strict and report["issue_count"]:
        raise SystemExit(7)


def cmd_verify_source_spans(args: argparse.Namespace) -> None:
    ws = Workspace(Path.cwd(), args.atlas, args.ngk_dir)
    report = evaluate_drift(ws, source_spans_only=True)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_drift_report(report)
    if args.strict and report["issue_count"]:
        raise SystemExit(7)


