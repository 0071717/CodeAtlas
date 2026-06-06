#!/usr/bin/env python3
"""Report library/framework capability gaps for CodeAtlas.

Missing library knowledge is not fatal, but it must be visible. This tool reads
`atlas/index/import-index.*`, classifies imports against a small built-in binding
registry, and writes reports consumed by no-MCP context packs.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
ATLAS = ROOT / "atlas"

BINDINGS: dict[str, dict[str, Any]] = {
    "react": {"patterns": ["react", "react-dom"], "surface": "frontend", "role": "React rendering", "support": "generic"},
    "react-router-dom": {"patterns": ["react-router-dom"], "surface": "frontend", "role": "routing/navigation", "support": "typed_seed"},
    "@tanstack/react-query": {"patterns": ["@tanstack/react-query", "react-query"], "surface": "frontend", "role": "server-state query/mutation/cache", "support": "typed_seed"},
    "@mui/material": {"patterns": ["@mui/material", "@mui/icons-material"], "surface": "frontend", "role": "UI components/forms/dialogs/tables", "support": "typed_seed"},
    "leaflet": {"patterns": ["leaflet", "react-leaflet"], "surface": "frontend", "role": "geospatial UI", "support": "typed_seed"},
    "regraph": {"patterns": ["regraph"], "surface": "frontend", "role": "graph visualization", "support": "typed_seed"},
    "axios": {"patterns": ["axios"], "surface": "frontend", "role": "HTTP client", "support": "generic"},
    "fastapi": {"patterns": ["fastapi"], "surface": "backend", "role": "routes/dependencies/middleware", "support": "typed_seed"},
    "starlette": {"patterns": ["starlette"], "surface": "backend", "role": "ASGI runtime", "support": "generic"},
    "pydantic": {"patterns": ["pydantic", "pydantic_settings"], "surface": "backend", "role": "schemas/settings", "support": "typed_seed"},
    "opensearch": {"patterns": ["opensearchpy", "opensearch_dsl", "opensearch"], "surface": "backend", "role": "search/query DSL", "support": "typed_seed"},
    "httpx": {"patterns": ["httpx", "requests"], "surface": "backend", "role": "HTTP client", "support": "generic"},
    "pytest": {"patterns": ["pytest", "unittest", "pytest_asyncio"], "surface": "testing", "role": "tests/fixtures", "support": "generic"},
    "playwright": {"patterns": ["@playwright/test", "playwright"], "surface": "testing", "role": "browser/e2e tests", "support": "planned"},
    "ngk": {"patterns": ["ngk"], "surface": "tooling", "role": "developer CLI", "support": "typed_seed"},
}

STDLIB = {"abc", "argparse", "ast", "asyncio", "collections", "contextlib", "copy", "csv", "dataclasses", "datetime", "decimal", "enum", "functools", "hashlib", "inspect", "io", "itertools", "json", "logging", "math", "os", "pathlib", "pickle", "random", "re", "shutil", "sqlite3", "statistics", "string", "subprocess", "sys", "tempfile", "threading", "time", "traceback", "typing", "uuid", "warnings"}
STDLIB.update(getattr(sys, "stdlib_module_names", set()))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: object) -> str:
    text = str(value).replace("\\", "/").strip("/")
    text = re.sub(r"[^A-Za-z0-9_./:@-]+", "_", text)
    text = text.replace("/", ".").replace("-", "_").replace(":", ".")
    return re.sub(r"\.+", ".", text).strip(".") or "root"


def candidates(path: Path) -> list[Path]:
    if path.suffix == ".json":
        return [path, path.with_suffix(".yaml")]
    if path.suffix == ".yaml":
        return [path.with_suffix(".json"), path]
    return [path]


def read(path: Path, default: Any) -> Any:
    for candidate in candidates(path):
        if candidate.exists():
            try:
                return json.loads(candidate.read_text(encoding="utf-8"))
            except Exception:
                return default
    return default


def write(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def import_root(name: str) -> str:
    raw = (name or "").strip()
    if not raw:
        return ""
    if raw.startswith("@"):
        parts = raw.split("/")
        return "/".join(parts[:2]) if len(parts) > 1 else raw
    if raw.startswith("."):
        return raw
    return re.split(r"[./]", raw, maxsplit=1)[0]


def is_internal(name: str, local_roots: set[str]) -> bool:
    raw = (name or "").strip()
    root = import_root(raw)
    return raw.startswith((".", "@/", "~/")) or raw.startswith(("src/", "app/", "components/", "features/", "lib/")) or root in local_roots


def local_roots() -> set[str]:
    roots: set[str] = set()
    for rec in read(ATLAS / "index" / "file-index.json", {}).get("files", []):
        path = str(rec.get("path", ""))
        if "/" in path:
            roots.add(path.split("/", 1)[0])
        elif path.endswith((".py", ".ts", ".tsx", ".js", ".jsx")):
            roots.add(Path(path).stem)
    return {r for r in roots if r not in {"test", "tests", "docs"}}


def binding_for(root: str) -> tuple[str | None, dict[str, Any] | None]:
    for key, binding in BINDINGS.items():
        if root == key or root in binding["patterns"]:
            return key, binding
    return None, None


def gap_risk(items: list[dict[str, Any]], root: str) -> str:
    text = " ".join(str(x.get("file", "")).lower() for x in items[:20])
    if any(t in text for t in ["route", "router", "client", "api", "query", "mutation", "store", "state"]):
        return "high"
    if any(t in text for t in ["component", "page", "form", "hook", "service", "schema"]):
        return "medium"
    return "medium" if root.startswith("@") else "low"


def main() -> int:
    imports = read(ATLAS / "index" / "import-index.json", {}).get("imports", [])
    roots = local_roots()
    counts: Counter[str] = Counter()
    supported: dict[str, dict[str, Any]] = {}
    unknown: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in imports:
        name = str(item.get("import", ""))
        root = import_root(name)
        binding_id, binding = binding_for(root)
        if binding:
            counts["supported"] += 1
            rec = supported.setdefault(binding_id, {"id": binding_id, **binding, "imports": set(), "files": set()})
            rec["imports"].add(name)
            rec["files"].add(f"{item.get('repo')}:{item.get('file')}")
        elif not root:
            counts["empty"] += 1
        elif root in STDLIB:
            counts["stdlib"] += 1
        elif is_internal(name, roots):
            counts["internal"] += 1
        else:
            counts["unknown"] += 1
            unknown[root].append(item)

    supported_out = []
    for rec in supported.values():
        rec = dict(rec)
        files = sorted(rec.pop("files"))
        imports_set = sorted(rec.pop("imports"))
        rec["file_count"] = len(files)
        rec["import_count"] = len(imports_set)
        rec["example_files"] = files[:10]
        rec["imports"] = imports_set[:20]
        supported_out.append(rec)

    gaps = []
    for root, items in sorted(unknown.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        files = sorted({f"{x.get('repo')}:{x.get('file')}" for x in items})
        gaps.append({
            "id": f"capability_gap.import.{slug(root)}",
            "type": "unsupported_import_binding",
            "import_root": root,
            "import_count": len(items),
            "file_count": len(files),
            "example_imports": sorted({str(x.get("import", "")) for x in items})[:10],
            "example_files": files[:10],
            "risk": gap_risk(items, root),
            "confidence": "medium" if len(items) > 1 else "low",
            "needs_review": True,
            "effect_on_atlas": [
                "Atlas can still index files, symbols, imports, and generic calls.",
                "Atlas must not infer framework-specific semantics for this library until a binding or extractor exists.",
                "Context packs should surface this warning when selected evidence passes through affected files."
            ],
            "suggested_binding_stub": {
                "id": root,
                "patterns": [root],
                "surface": "unknown",
                "semantic_role": "TODO",
                "extractor": "TODO",
                "support": "unsupported"
            }
        })

    total_external = counts["supported"] + counts["unknown"]
    report = {
        "generated_at": now(),
        "status": "needs_review" if gaps else "ok",
        "mcp_required": False,
        "summary": {
            "import_record_count": len(imports),
            "supported_import_records": counts["supported"],
            "unknown_import_records": counts["unknown"],
            "ignored_stdlib_records": counts["stdlib"],
            "ignored_internal_records": counts["internal"],
            "capability_gap_count": len(gaps),
            "framework_binding_coverage_ratio": round((counts["supported"] / total_external) if total_external else 1.0, 4),
        },
        "supported_bindings": sorted(supported_out, key=lambda x: x["id"]),
        "capability_gaps": gaps,
        "policy": {
            "missing_library_rule": "Missing library bindings are not fatal; they lower confidence and block framework-specific claims.",
            "llm_rule": "Do not infer semantics for unsupported imports unless source evidence directly proves the behavior.",
            "no_mcp_contract": "This is a local filesystem artifact consumed by CLI tools and context packs."
        }
    }

    write(ATLAS / "bindings" / "library-capabilities.json", report)
    write(ATLAS / "audit" / "capability-gaps.json", report)
    write(ATLAS / "audit" / "unsupported-capabilities.json", {
        "generated_at": report["generated_at"],
        "mcp_required": False,
        "summary": report["summary"],
        "unsupported_capabilities": gaps,
    })
    print("capability-audit", f"supported={counts['supported']}", f"unknown={counts['unknown']}", f"gaps={len(gaps)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
