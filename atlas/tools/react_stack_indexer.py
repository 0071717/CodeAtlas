#!/usr/bin/env python3
"""React stack candidate indexer for CodeAtlas V2.

Fast dependency-light candidate extractor for React Router DOM, TanStack Query,
Material UI, Leaflet/react-leaflet, and ReGraph. This is not a final TS parser;
it creates bounded packets for later ts-morph/tree-sitter hardening and Kiro AI enrichment.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
ATLAS = ROOT / "atlas"
CONFIG = ATLAS / "config" / "project.yaml"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: object) -> str:
    text = str(value).replace("\\", "/").strip("/")
    text = re.sub(r"[^A-Za-z0-9_./:-]+", "_", text)
    return re.sub(r"[./:-]+", "-", text).strip("-").lower() or "root"


def read(path: Path, default: Any) -> Any:
    for candidate in [path, path.with_suffix(".yaml") if path.suffix == ".json" else path.with_suffix(".json")]:
        if candidate.exists():
            try:
                return json.loads(candidate.read_text(encoding="utf-8"))
            except Exception:
                return default
    return default


def write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def repos() -> list[dict[str, Any]]:
    if not CONFIG.exists():
        return []
    out: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    inside = False
    for line in CONFIG.read_text(encoding="utf-8").splitlines():
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
            out.append(current)
            continue
        prop_match = re.match(r"^\s{4}([\w.-]+):\s*(.*?)\s*$", line)
        if current and prop_match:
            current[prop_match.group(1)] = prop_match.group(2).strip("'\"")
    for repo in out:
        path = Path(repo.get("path", ""))
        repo["path"] = path if path.is_absolute() else (ROOT / path).resolve()
        repo["role"] = repo.get("role") or repo.get("type", "unknown")
    return [r for r in out if r.get("path")]


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def import_names(text: str, package: str) -> list[str]:
    names: set[str] = set()
    pattern = re.compile(r"import\s+(.+?)\s+from\s+['\"]" + re.escape(package) + r"['\"]", re.S)
    for match in pattern.finditer(text):
        body = match.group(1).replace("\n", " ")
        brace = re.search(r"\{([^}]+)\}", body)
        if brace:
            for item in brace.group(1).split(","):
                item = item.strip().split(" as ")[0].strip()
                if item:
                    names.add(item)
        else:
            first = body.split(",")[0].strip()
            if first:
                names.add(first)
    return sorted(names)


def main() -> None:
    parser = argparse.ArgumentParser(description="Index React Router DOM, TanStack Query, MUI, Leaflet, and ReGraph candidates.")
    parser.add_argument("--file-index", default="atlas/index/file-index.json")
    args = parser.parse_args()

    files = read(ROOT / args.file_index, {}).get("files", [])
    if not files:
        raise SystemExit("No file index found. Run python3 atlas/tools/codeatlas_v2_suite.py snapshot first.")

    repo_by_id = {r["id"]: r for r in repos()}
    routes: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []
    mui: list[dict[str, Any]] = []
    leaflet: list[dict[str, Any]] = []
    regraph: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []

    for rec in files:
        if rec.get("language") not in {"typescript", "typescript-react", "javascript", "javascript-react"}:
            continue
        repo = repo_by_id.get(rec["repo"])
        path = repo and repo["path"] / rec["path"]
        if not path or not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            findings.append({"type": "read_error", "repo": rec["repo"], "file": rec["path"], "reason": str(exc)})
            continue

        for pattern, kind in [(r"<Route[^>]+path\s*=\s*['\"]([^'\"]+)['\"]", "jsx_route"), (r"\bpath\s*:\s*['\"]([^'\"]+)['\"]", "object_route"), (r"\bnavigate\s*\(\s*['\"]([^'\"]+)['\"]", "navigate_target")]:
            for match in re.finditer(pattern, text):
                routes.append({"id": f"route.{rec['repo']}.{slug(match.group(1))}", "repo": rec["repo"], "file": rec["path"], "path": match.group(1), "kind": kind, "line_start": line_number(text, match.start()), "confidence": "medium", "needs_review": kind != "jsx_route"})

        for match in re.finditer(r"\b(useQuery|useMutation|useInfiniteQuery)\s*\((?P<body>[\s\S]{0,1200}?)\)\s*[;,\n]", text):
            body = match.group("body")
            key_match = re.search(r"queryKey\s*:\s*(\[[^\]]+\])", body)
            fn_match = re.search(r"(queryFn|mutationFn)\s*:\s*([A-Za-z0-9_.$]+)", body)
            queries.append({"id": f"tanstack.{rec['repo']}.{slug(rec['path'])}.{match.group(1)}.{len(queries)+1}", "repo": rec["repo"], "file": rec["path"], "hook": match.group(1), "kind": "mutation" if match.group(1) == "useMutation" else "query", "query_key": key_match.group(1) if key_match else None, "function_ref": fn_match.group(2) if fn_match else None, "line_start": line_number(text, match.start()), "confidence": "medium", "needs_review": True})

        for package, target, semantic in [("@mui/material", mui, "ui_component_library"), ("@mui/icons-material", mui, "ui_component_library"), ("react-leaflet", leaflet, "geospatial_ui"), ("leaflet", leaflet, "geospatial_ui"), ("regraph", regraph, "graph_visualization_ui"), ("@cambridge-intelligence/regraph", regraph, "graph_visualization_ui")]:
            for name in import_names(text, package):
                count = len(re.findall(r"<" + re.escape(name) + r"(\s|>|/)", text))
                target.append({"id": f"library.{rec['repo']}.{slug(rec['path'])}.{slug(package)}.{slug(name)}", "repo": rec["repo"], "file": rec["path"], "package": package, "component": name, "semantic_role": semantic, "usage_count": count, "confidence": "high" if count else "medium", "needs_review": count == 0})

        for pattern, kind in [(r"<form[^>]+onSubmit\s*=\s*\{([^}]+)\}", "form_submit"), (r"<Button[^>]+onClick\s*=\s*\{([^}]+)\}", "button_click"), (r"\bonClick\s*=\s*\{([^}]+)\}", "click_handler")]:
            for match in re.finditer(pattern, text):
                actions.append({"id": f"action.{rec['repo']}.{slug(rec['path'])}.{kind}.{len(actions)+1}", "repo": rec["repo"], "file": rec["path"], "kind": kind, "handler": match.group(1).strip(), "line_start": line_number(text, match.start()), "confidence": "medium", "needs_review": True})

    write(ATLAS / "index/react-router-index.json", {"generated_at": now(), "routes": routes})
    write(ATLAS / "index/tanstack-query-index.json", {"generated_at": now(), "queries": queries})
    write(ATLAS / "index/material-ui-index.json", {"generated_at": now(), "mui_components": mui})
    write(ATLAS / "index/leaflet-index.json", {"generated_at": now(), "leaflet_components": leaflet})
    write(ATLAS / "index/regraph-index.json", {"generated_at": now(), "regraph_components": regraph})
    write(ATLAS / "index/ui-action-index.json", {"generated_at": now(), "actions": actions})
    write(ATLAS / "map/react-ui-stack-map.json", {"generated_at": now(), "counts": {"routes": len(routes), "queries": len(queries), "mui": len(mui), "leaflet": len(leaflet), "regraph": len(regraph), "actions": len(actions)}, "notes": ["Candidate extraction only. Use TypeScript AST hardening and Kiro packet enrichment next."]})
    write(ATLAS / "audit/react-stack-indexer-report.json", {"generated_at": now(), "status": "ok", "findings": findings})
    print("react-stack", len(routes), len(queries), len(mui), len(leaflet), len(regraph), len(actions))


if __name__ == "__main__":
    main()
