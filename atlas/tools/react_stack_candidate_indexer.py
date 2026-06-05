#!/usr/bin/env python3
"""React stack candidate indexer for CodeAtlas.

Heuristic, dependency-light extraction for React Router DOM, TanStack Query,
and Material UI candidates. This complements codeatlas_v2_suite.py and gives
AI-assisted workers smaller, better bounded inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
ATLAS = ROOT / "atlas"
CONFIG = ATLAS / "config" / "project.yaml"
IGNORE_DIRS = {".git", "node_modules", "dist", "build", "coverage", ".next", ".cache"}
FRONTEND_EXTS = {".ts", ".tsx", ".js", ".jsx"}
ROUTER_TOKENS = ["createBrowserRouter", "createRoutesFromElements", "RouterProvider", "BrowserRouter", "Routes", "Route", "useRoutes", "Navigate", "useNavigate", "useParams", "useSearchParams", "Outlet"]
TANSTACK_TOKENS = ["useQuery", "useMutation", "useInfiniteQuery", "invalidateQueries", "setQueryData", "refetchQueries"]
MUI_COMPONENTS = ["TextField", "Select", "Autocomplete", "Checkbox", "RadioGroup", "Button", "IconButton", "LoadingButton", "Dialog", "Drawer", "Snackbar", "Alert", "DataGrid", "Table", "Tabs", "Menu", "FormControl", "FormHelperText"]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: object) -> str:
    text = str(value).replace("\\", "/").strip("/")
    text = re.sub(r"[^A-Za-z0-9_./:-]+", "_", text)
    return re.sub(r"\.+", ".", text.replace("/", ".").replace("-", "_").replace(":", ".")).strip(".") or "root"


def write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def simple_project_parser(text: str) -> list[dict[str, Any]]:
    repos: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    inside = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("repositories:"):
            inside = True
            continue
        if inside and re.match(r"^[^\s].*:", line):
            inside = False
        if not inside or not line.strip() or line.lstrip().startswith("#"):
            continue
        repo_match = re.match(r"^\s{2}([\w.-]+):\s*$", line)
        if repo_match:
            current = {"id": repo_match.group(1)}
            repos.append(current)
            continue
        prop_match = re.match(r"^\s{4}([\w.-]+):\s*(.*?)\s*$", line)
        if current and prop_match:
            current[prop_match.group(1)] = prop_match.group(2).strip("'\"")
    return repos


def configured_repos() -> list[dict[str, Any]]:
    if not CONFIG.exists():
        return []
    text = CONFIG.read_text(encoding="utf-8")
    repos = simple_project_parser(text)
    result = []
    for repo in repos:
        role = repo.get("role") or repo.get("type") or "unknown"
        framework = repo.get("framework") or ""
        language = repo.get("language") or ""
        if "front" not in role and framework != "react" and language != "typescript":
            continue
        path = Path(str(repo.get("path", "")))
        full_path = path if path.is_absolute() else (ROOT / path).resolve()
        result.append({"id": repo.get("id"), "path": full_path, "role": role, "framework": framework, "language": language})
    return result


def evidence(repo_id: str, rel: str, line: int, symbol: str | None = None) -> list[dict[str, Any]]:
    item: dict[str, Any] = {"type": "code", "repo": repo_id, "file": rel, "line_start": line, "line_end": line}
    if symbol:
        item["symbol"] = symbol
    return [item]


def extract_file(repo_id: str, rel: str, text: str) -> dict[str, list[dict[str, Any]]]:
    router: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []
    mui: list[dict[str, Any]] = []
    states: list[dict[str, Any]] = []

    for token in ROUTER_TOKENS:
        for match in re.finditer(rf"\b{token}\b", text):
            line = line_of(text, match.start())
            router.append({"id": f"react_router.{repo_id}.{slug(rel)}.{token}.{line}", "repo": repo_id, "file": rel, "kind": token, "line_start": line, "confidence": "medium", "needs_review": True, "evidence": evidence(repo_id, rel, line)})

    for match in re.finditer(r"<Route[^>]+path=[{\s]*[`\"']([^`\"']+)[`\"']", text):
        line = line_of(text, match.start())
        router.append({"id": f"route.{repo_id}.{slug(match.group(1))}", "repo": repo_id, "file": rel, "path": match.group(1), "kind": "Route", "line_start": line, "confidence": "medium", "needs_review": True, "evidence": evidence(repo_id, rel, line)})

    for token in TANSTACK_TOKENS:
        for match in re.finditer(rf"\b{token}\s*\(", text):
            line = line_of(text, match.start())
            kind = "query" if token in {"useQuery", "useInfiniteQuery"} else "mutation" if token == "useMutation" else "cache_effect"
            queries.append({"id": f"tanstack.{kind}.{repo_id}.{slug(rel)}.{token}.{line}", "repo": repo_id, "file": rel, "kind": kind, "call": token, "line_start": line, "confidence": "medium", "needs_review": True, "evidence": evidence(repo_id, rel, line)})

    for token in ["isLoading", "isPending", "isFetching", "isError", "isSuccess", "error", "data"]:
        for match in re.finditer(rf"\b{token}\b", text):
            line = line_of(text, match.start())
            states.append({"id": f"state_hint.{repo_id}.{slug(rel)}.{token}.{line}", "repo": repo_id, "file": rel, "state_hint": token, "line_start": line, "confidence": "low", "needs_review": True, "evidence": evidence(repo_id, rel, line)})

    for component in MUI_COMPONENTS:
        for match in re.finditer(rf"<{component}\b", text):
            line = line_of(text, match.start())
            kind = "action" if component in {"Button", "IconButton", "LoadingButton", "MenuItem"} else "field" if component in {"TextField", "Select", "Autocomplete", "Checkbox", "RadioGroup", "FormControl", "FormHelperText"} else "display_state"
            mui.append({"id": f"mui.{kind}.{repo_id}.{slug(rel)}.{component}.{line}", "repo": repo_id, "file": rel, "component": component, "kind": kind, "line_start": line, "confidence": "medium", "needs_review": True, "evidence": evidence(repo_id, rel, line)})

    return {"react_router": router, "tanstack_query": queries, "material_ui": mui, "ui_state_hints": states}


def run(_: argparse.Namespace) -> None:
    all_router: list[dict[str, Any]] = []
    all_queries: list[dict[str, Any]] = []
    all_mui: list[dict[str, Any]] = []
    all_states: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for repo in configured_repos():
        if not repo["path"].exists():
            missing.append({"repo": repo["id"], "path": str(repo["path"]), "reason": "missing frontend repo"})
            continue
        for root, dirs, names in os.walk(repo["path"]):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for name in names:
                path = Path(root) / name
                if path.suffix.lower() not in FRONTEND_EXTS:
                    continue
                rel = str(path.relative_to(repo["path"])).replace("\\", "/")
                try:
                    text = path.read_text(encoding="utf-8")
                except Exception:
                    continue
                result = extract_file(str(repo["id"]), rel, text)
                all_router.extend(result["react_router"])
                all_queries.extend(result["tanstack_query"])
                all_mui.extend(result["material_ui"])
                all_states.extend(result["ui_state_hints"])
    write(ATLAS / "index/react-router-index.yaml", {"generated_at": now(), "react_router": all_router})
    write(ATLAS / "index/tanstack-query-index.yaml", {"generated_at": now(), "tanstack_query": all_queries})
    write(ATLAS / "index/material-ui-index.yaml", {"generated_at": now(), "material_ui": all_mui})
    write(ATLAS / "map/ui-state-candidates.yaml", {"generated_at": now(), "ui_state_hints": all_states})
    write(ATLAS / "audit/react-stack-indexer-report.yaml", {"generated_at": now(), "router_count": len(all_router), "tanstack_count": len(all_queries), "material_ui_count": len(all_mui), "state_hint_count": len(all_states), "missing": missing})
    print("react-stack", len(all_router), len(all_queries), len(all_mui), len(all_states))


def main() -> None:
    parser = argparse.ArgumentParser(description="Index React Router DOM, TanStack Query, and Material UI candidates")
    parser.set_defaults(func=run)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
