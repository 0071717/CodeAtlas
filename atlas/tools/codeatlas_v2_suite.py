#!/usr/bin/env python3
"""CodeAtlas V2 deterministic foundation suite.

Readable, dependency-light tooling for source snapshots, AST-derived indexes,
runtime/config/test indexes, graph/flow seeds, drift reports, validation reports,
and visualizer exports.

Output files use JSON syntax with `.yaml` extensions. JSON is valid YAML and is
easy for Kiro and Python standard library tools to parse deterministically.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
ATLAS = ROOT / "atlas"
CONFIG = ATLAS / "config" / "project.yaml"

IGNORE_DIRS = {
    ".git", "node_modules", "dist", "build", "coverage", ".venv", "venv",
    "__pycache__", ".next", ".cache", ".mypy_cache", ".pytest_cache",
}
SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx"}
CONFIG_EXTS = {".yaml", ".yml", ".json", ".toml", ".ini", ".env"}
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


@dataclass
class Repo:
    id: str
    path: Path
    role: str = "unknown"
    language: str | None = None
    framework: str | None = None
    name: str | None = None

    def exists(self) -> bool:
        return self.path.exists()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: object) -> str:
    text = str(value).replace("\\", "/").strip("/")
    text = re.sub(r"[^A-Za-z0-9_./:-]+", "_", text)
    text = text.replace("/", ".").replace("-", "_").replace(":", ".")
    return re.sub(r"\.+", ".", text).strip(".") or "root"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def ensure_dirs() -> None:
    for rel in """
source index architecture map payloads bindings runtime graph errors flows facts rules requirements testing
knowledge/nodes knowledge/indexes knowledge/graph knowledge/cards audit change
visualizer plans tools-output
""".split():
        (ATLAS / rel).mkdir(parents=True, exist_ok=True)


def run_git(repo_path: Path, *args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo_path), *args],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return None


def worktree_dirty(repo: "Repo") -> bool | None:
    """Return True/False if the repo's worktree is dirty, or None if it is not a
    git repo (so callers can distinguish "clean" from "unknown")."""
    status = run_git(repo.path, "status", "--porcelain")
    if status is None:
        return None
    return bool(status.strip())


def simple_project_parser(text: str) -> dict[str, Any]:
    """Small fallback parser for the existing atlas/config/project.yaml shape."""
    repositories: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    inside_repos = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("repositories:"):
            inside_repos = True
            continue
        if inside_repos and re.match(r"^[^\s].*:", line):
            inside_repos = False
        if not inside_repos or not line.strip() or line.lstrip().startswith("#"):
            continue
        repo_match = re.match(r"^\s{2}([\w.-]+):\s*$", line)
        if repo_match:
            repo_id = repo_match.group(1)
            current = {"id": repo_id}
            repositories[repo_id] = current
            continue
        prop_match = re.match(r"^\s{4}([\w.-]+):\s*(.*?)\s*$", line)
        if current and prop_match:
            current[prop_match.group(1)] = prop_match.group(2).strip("'\"")
    return {"repositories": repositories}


def load_project_config() -> dict[str, Any]:
    if not CONFIG.exists():
        return {"repositories": {}}
    text = CONFIG.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text)
        if isinstance(loaded, dict):
            return loaded
    except Exception:
        pass
    return simple_project_parser(text)


def repos() -> list[Repo]:
    cfg = load_project_config()
    raw_repos = cfg.get("repositories", {})
    result: list[Repo] = []
    if isinstance(raw_repos, dict):
        items = raw_repos.items()
    elif isinstance(raw_repos, list):
        items = [(x.get("id", f"repo_{i}"), x) for i, x in enumerate(raw_repos) if isinstance(x, dict)]
    else:
        items = []
    for repo_id, raw in items:
        if not isinstance(raw, dict):
            continue
        path = Path(str(raw.get("path", "")))
        if not path:
            continue
        full_path = path if path.is_absolute() else (ROOT / path).resolve()
        result.append(
            Repo(
                id=str(raw.get("id") or repo_id),
                name=raw.get("name"),
                path=full_path,
                role=str(raw.get("role") or raw.get("type") or "unknown"),
                language=raw.get("language"),
                framework=raw.get("framework"),
            )
        )
    return result


def language_for(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript-react",
        ".js": "javascript",
        ".jsx": "javascript-react",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".toml": "toml",
        ".md": "markdown",
    }.get(ext, "unknown")


def classification_for(path: str) -> str:
    ext = Path(path).suffix.lower()
    low = f"/{path.lower()}"
    if any(token in low for token in ["/test/", "/tests/", ".spec.", ".test.", "conftest.py"]):
        return "test"
    if ext in SOURCE_EXTS:
        return "source"
    if ext in CONFIG_EXTS:
        return "config"
    if ext == ".md":
        return "documentation"
    return "asset"


def analysis_depth(role: str, rel: str, classification: str) -> str:
    low = rel.lower()
    if classification == "asset":
        return "tracked"
    if classification == "documentation":
        return "shallow"
    if classification == "config":
        return "medium"
    if classification == "test":
        return "deep"
    deep_markers = [
        "/routers/", "/routes/", "/services/", "/schemas/", "/models/", "/os/",
        "middleware", "dependency", "permission", "auth", "api", "client",
        "page", "component", "hook", "form",
    ]
    if classification == "source" and any(m in low for m in deep_markers):
        return "deep"
    if role in {"fastapi_backend", "backend", "react_frontend", "frontend"} and classification == "source":
        return "medium"
    return "shallow"


def scan_files() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    files: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for repo in repos():
        if not repo.exists():
            missing.append({"repo": repo.id, "path": str(repo.path), "reason": "missing repo"})
            continue
        for root, dirs, names in os.walk(repo.path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for name in names:
                path = Path(root) / name
                if any(part in IGNORE_DIRS for part in path.parts):
                    continue
                try:
                    data = path.read_bytes()
                except Exception as exc:
                    missing.append({"repo": repo.id, "path": str(path), "reason": str(exc)})
                    continue
                rel = str(path.relative_to(repo.path)).replace("\\", "/")
                lang = language_for(rel)
                classification = classification_for(rel)
                files.append(
                    {
                        "id": f"file.{repo.id}.{slug(rel)}",
                        "repo": repo.id,
                        "repo_role": repo.role,
                        "path": rel,
                        "language": lang,
                        "classification": classification,
                        "analysis_depth": analysis_depth(repo.role, rel, classification),
                        "line_count": data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0),
                        "size_bytes": len(data),
                        "sha256": sha256_bytes(data),
                    }
                )
    return sorted(files, key=lambda x: (x["repo"], x["path"])), missing


def code_evidence(rec: dict[str, Any], symbol: str | None = None, start: int | None = None, end: int | None = None) -> list[dict[str, Any]]:
    ev: dict[str, Any] = {"type": "code", "repo": rec["repo"], "file": rec["path"]}
    if symbol:
        ev["symbol"] = symbol
    if start:
        ev["line_start"] = start
    if end:
        ev["line_end"] = end
    return [ev]


def call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{call_name(node.value)}.{node.attr}".strip(".")
    if isinstance(node, ast.Call):
        return call_name(node.func)
    if isinstance(node, ast.Subscript):
        return call_name(node.value)
    return ""


def literal_value(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Str):
        return node.s
    return None


def annotation_text(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    return ast.unparse(node) if hasattr(ast, "unparse") else type(node).__name__


def arg_signature(arg: ast.arg, prefix: str = "") -> str:
    annotation = annotation_text(arg.annotation)
    return f"{prefix}{arg.arg}: {annotation}" if annotation else f"{prefix}{arg.arg}"


def signature_for(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> str:
    if isinstance(node, ast.ClassDef):
        return f"class {node.name}"
    parts = [arg_signature(arg) for arg in node.args.args]
    if node.args.vararg:
        parts.append(arg_signature(node.args.vararg, "*"))
    if node.args.kwarg:
        parts.append(arg_signature(node.args.kwarg, "**"))
    returns = annotation_text(node.returns)
    suffix = f" -> {returns}" if returns else ""
    return f"{node.name}({', '.join(parts)}){suffix}"


def import_names(tree: ast.AST) -> list[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                names.add(f"{module}.{alias.name}".strip("."))
    return sorted(names)


def branch_summaries(node: ast.AST) -> list[dict[str, Any]]:
    branches: list[dict[str, Any]] = []
    for idx, child in enumerate(ast.walk(node), start=1):
        if isinstance(child, ast.If):
            branches.append(
                {
                    "id": f"branch_{idx}",
                    "condition_type": type(child.test).__name__,
                    "condition_source": ast.unparse(child.test) if hasattr(ast, "unparse") else type(child.test).__name__,
                    "has_else": bool(child.orelse),
                    "confidence": "medium",
                    "needs_review": True,
                }
            )
    return branches[:50]


def raise_summaries(node: ast.AST) -> list[str]:
    raises: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Raise) and child.exc is not None:
            raises.add(call_name(child.exc) or type(child.exc).__name__)
    return sorted(raises)


def python_indexes(repo: Repo, rec: dict[str, Any], path: Path, text: str) -> dict[str, list[dict[str, Any]]]:
    result = {k: [] for k in ["symbols", "imports", "endpoints", "schemas", "services", "data_access", "runtime", "tests"]}
    try:
        tree = ast.parse(text)
    except Exception as exc:
        result["runtime"].append({"id": f"parse_error.{rec['repo']}.{slug(rec['path'])}", "type": "parse_error", "repo": rec["repo"], "file": rec["path"], "error": str(exc), "needs_review": True, "confidence": "low"})
        return result

    for imp in import_names(tree):
        result["imports"].append({"id": f"import.{rec['repo']}.{slug(rec['path'])}.{slug(imp)}", "repo": rec["repo"], "file": rec["path"], "import": imp})

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = getattr(node, "lineno", 1)
            end = getattr(node, "end_lineno", start)
            source = "\n".join(text.splitlines()[start - 1 : end])
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            symbol_id = f"symbol.{rec['repo']}.{slug(Path(rec['path']).with_suffix('').as_posix())}.{node.name}"
            calls = sorted({call_name(c.func) for c in ast.walk(node) if isinstance(c, ast.Call) and call_name(c.func)})[:150]
            decorators = [call_name(d.func if isinstance(d, ast.Call) else d) for d in getattr(node, "decorator_list", [])]
            evidence = code_evidence(rec, node.name, start, end)
            symbol = {
                "id": symbol_id,
                "repo": rec["repo"],
                "file": rec["path"],
                "name": node.name,
                "kind": kind,
                "signature": signature_for(node),
                "signature_hash": sha256_text(signature_for(node)),
                "body_hash": sha256_text(source),
                "line_start": start,
                "line_end": end,
                "decorators": decorators,
                "calls": calls,
                "branches": branch_summaries(node),
                "raises": raise_summaries(node),
                "confidence": "high",
                "needs_review": False,
                "evidence": evidence,
            }
            result["symbols"].append(symbol)

            if isinstance(node, ast.ClassDef):
                bases = [call_name(b) for b in node.bases]
                if any(base.endswith("BaseModel") or "pydantic" in base.lower() for base in bases):
                    fields = []
                    for stmt in node.body:
                        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                            fields.append({"name": stmt.target.id, "annotation": ast.unparse(stmt.annotation) if hasattr(ast, "unparse") else type(stmt.annotation).__name__})
                    result["schemas"].append({"id": f"schema.{rec['repo']}.{slug(node.name)}", "repo": rec["repo"], "file": rec["path"], "name": node.name, "fields": fields, "source_symbol": symbol_id, "confidence": "high", "needs_review": False, "evidence": evidence})

            if kind == "function":
                low_path = rec["path"].lower()
                if "/services/" in f"/{low_path}" or low_path.endswith("_service.py") or "service" in node.name.lower():
                    result["services"].append({"id": f"service.{rec['repo']}.{slug(node.name)}", "repo": rec["repo"], "file": rec["path"], "function": node.name, "source_symbol": symbol_id, "calls": calls, "confidence": "medium", "needs_review": True, "evidence": evidence})
                if "/os/" in f"/{low_path}" or low_path.endswith("_os.py") or any(tok in low_path for tok in ["repository", "dao", "data_access"]):
                    result["data_access"].append({"id": f"data_access.{rec['repo']}.{slug(node.name)}", "repo": rec["repo"], "file": rec["path"], "function": node.name, "source_symbol": symbol_id, "calls": calls, "confidence": "medium", "needs_review": True, "evidence": evidence})
                if rec["classification"] == "test" or node.name.startswith("test_"):
                    result["tests"].append({"id": f"test.{rec['repo']}.{slug(rec['path'])}.{node.name}", "repo": rec["repo"], "file": rec["path"], "function": node.name, "fixtures_or_args": [a.arg for a in node.args.args], "source_symbol": symbol_id, "confidence": "medium", "needs_review": True, "evidence": evidence})

            for dec in getattr(node, "decorator_list", []):
                dec_call = dec if isinstance(dec, ast.Call) else None
                dec_name = call_name(dec_call.func if dec_call else dec)
                short = dec_name.split(".")[-1].lower()
                if isinstance(dec_call, ast.Call) and short in HTTP_METHODS:
                    route_path = literal_value(dec_call.args[0]) if dec_call.args else None
                    endpoint_id = f"endpoint.{rec['repo']}.{slug(short + '.' + str(route_path or node.name))}"
                    result["endpoints"].append(
                        {
                            "id": endpoint_id,
                            "repo": rec["repo"],
                            "file": rec["path"],
                            "method": short.upper(),
                            "path": route_path,
                            "handler": node.name,
                            "source_symbol": symbol_id,
                            "calls": calls,
                            "branches": branch_summaries(node),
                            "raises": raise_summaries(node),
                            "confidence": "high" if route_path else "medium",
                            "needs_review": route_path is None,
                            "evidence": evidence,
                        }
                    )
                if "middleware" in dec_name.lower():
                    result["runtime"].append({"id": f"middleware.{rec['repo']}.{slug(node.name)}", "type": "middleware", "repo": rec["repo"], "file": rec["path"], "symbol": node.name, "source_symbol": symbol_id, "confidence": "medium", "needs_review": True, "evidence": evidence})
                if "exception_handler" in dec_name.lower():
                    result["runtime"].append({"id": f"exception_handler.{rec['repo']}.{slug(node.name)}", "type": "exception_handler", "repo": rec["repo"], "file": rec["path"], "symbol": node.name, "source_symbol": symbol_id, "confidence": "medium", "needs_review": True, "evidence": evidence})

    for call in [n for n in ast.walk(tree) if isinstance(n, ast.Call)]:
        cname = call_name(call.func)
        lineno = getattr(call, "lineno", None)
        if cname.endswith("add_middleware"):
            result["runtime"].append({"id": f"middleware.{rec['repo']}.{slug(rec['path'])}.{lineno}", "type": "middleware_registration", "repo": rec["repo"], "file": rec["path"], "line_start": lineno, "confidence": "high", "needs_review": False, "evidence": code_evidence(rec, None, lineno, lineno)})
        if cname.endswith("Depends"):
            dep = ast.unparse(call.args[0]) if call.args and hasattr(ast, "unparse") else None
            result["runtime"].append({"id": f"dependency.{rec['repo']}.{slug(rec['path'])}.{lineno}", "type": "dependency", "repo": rec["repo"], "file": rec["path"], "dependency": dep, "line_start": lineno, "confidence": "medium", "needs_review": True, "evidence": code_evidence(rec, None, lineno, lineno)})
    return result


def ts_indexes(repo: Repo, rec: dict[str, Any], text: str) -> dict[str, list[dict[str, Any]]]:
    result = {k: [] for k in ["symbols", "routes", "components", "hooks", "api_clients", "ui_actions", "tests", "imports"]}
    for match in re.finditer(r"import\s+(?:.*?)\s+from\s+[`\"']([^`\"']+)[`\"']", text, re.S):
        result["imports"].append({"id": f"import.{rec['repo']}.{slug(rec['path'])}.{slug(match.group(1))}", "repo": rec["repo"], "file": rec["path"], "import": match.group(1)})
    for match in re.finditer(r"(?:export\s+)?(?:async\s+)?(?:function|const|class)\s+([A-Z_a-z][A-Za-z0-9_]*)", text):
        name = match.group(1)
        line = text.count("\n", 0, match.start()) + 1
        symbol_id = f"symbol.{rec['repo']}.{slug(Path(rec['path']).with_suffix('').as_posix())}.{name}"
        kind = "component" if name[:1].isupper() and rec["language"].endswith("react") else "hook" if name.startswith("use") else "symbol"
        item = {"id": symbol_id, "repo": rec["repo"], "file": rec["path"], "name": name, "kind": kind, "line_start": line, "line_end": line, "confidence": "medium", "needs_review": True, "evidence": code_evidence(rec, name, line, line)}
        result["symbols"].append(item)
        if kind == "component":
            result["components"].append({"id": f"component.{rec['repo']}.{slug(name)}", "repo": rec["repo"], "file": rec["path"], "name": name, "source_symbol": symbol_id, "confidence": "medium", "needs_review": True, "evidence": item["evidence"]})
        if kind == "hook":
            result["hooks"].append({"id": f"hook.{rec['repo']}.{slug(name)}", "repo": rec["repo"], "file": rec["path"], "name": name, "source_symbol": symbol_id, "confidence": "medium", "needs_review": True, "evidence": item["evidence"]})
        if rec["classification"] == "test" or name.lower().startswith(("test", "spec")):
            result["tests"].append({"id": f"test.{rec['repo']}.{slug(rec['path'])}.{slug(name)}", "repo": rec["repo"], "file": rec["path"], "function": name, "source_symbol": symbol_id, "confidence": "medium", "needs_review": True})
    for match in re.finditer(r"<Route[^>]+path=[{\s]*[`\"']([^`\"']+)[`\"']", text):
        line = text.count("\n", 0, match.start()) + 1
        result["routes"].append({"id": f"route.{rec['repo']}.{slug(match.group(1))}", "repo": rec["repo"], "file": rec["path"], "path": match.group(1), "line_start": line, "confidence": "medium", "needs_review": True, "evidence": code_evidence(rec, None, line, line)})
    for match in re.finditer(r"(fetch|axios\.[a-z]+|client\.[a-z]+)\s*\(\s*([`\"'])([^`\"']+)\2", text, re.I):
        line = text.count("\n", 0, match.start()) + 1
        method = match.group(1).split(".")[-1].upper() if "." in match.group(1) else "UNKNOWN"
        result["api_clients"].append({"id": f"api.{rec['repo']}.{slug(rec['path'])}.{slug(match.group(3))}", "repo": rec["repo"], "file": rec["path"], "method": method, "path": match.group(3), "line_start": line, "confidence": "medium", "needs_review": True, "evidence": code_evidence(rec, None, line, line)})
    for match in re.finditer(r"(onClick|onSubmit|onChange)\s*=\s*{([^}]+)}", text):
        line = text.count("\n", 0, match.start()) + 1
        result["ui_actions"].append({"id": f"action.{rec['repo']}.{slug(rec['path'])}.{line}", "repo": rec["repo"], "file": rec["path"], "event": match.group(1), "handler": match.group(2).strip(), "line_start": line, "confidence": "medium", "needs_review": True, "evidence": code_evidence(rec, None, line, line)})
    return result


def cmd_init(_: argparse.Namespace) -> None:
    ensure_dirs()
    write(ATLAS / "audit/v2-init-report.yaml", {"generated_at": now(), "status": "ok"})
    print("init")


def cmd_snapshot(_: argparse.Namespace) -> None:
    ensure_dirs()
    files, missing = scan_files()
    repo_records = []
    for repo in repos():
        repo_records.append(
            {
                "id": repo.id,
                "name": repo.name,
                "path": str(repo.path),
                "role": repo.role,
                "language": repo.language,
                "framework": repo.framework,
                "exists": repo.exists(),
                "git_branch": run_git(repo.path, "rev-parse", "--abbrev-ref", "HEAD") if repo.exists() else None,
                "git_commit": run_git(repo.path, "rev-parse", "HEAD") if repo.exists() else None,
                "dirty_worktree": worktree_dirty(repo) if repo.exists() else None,
            }
        )
    commits = [r.get("git_commit") for r in repo_records if r.get("git_commit")]
    snapshot_doc = {
        "generated_at": now(),
        # indexed_commit is the single-repo convenience scalar; indexed_commits
        # is the per-repo map for multi-repo projects. dirty_worktree is True if
        # any repo had uncommitted changes when the snapshot was taken.
        "indexed_commit": commits[0] if len(commits) == 1 else None,
        "indexed_commits": {r["id"]: r.get("git_commit") for r in repo_records},
        "dirty_worktree": any(bool(r.get("dirty_worktree")) for r in repo_records),
        "repositories": repo_records,
        "file_count": len(files),
        "missing": missing,
    }
    write(ATLAS / "source/file-hashes.yaml", {"generated_at": now(), "files": files})
    write(ATLAS / "index/file-index.yaml", {"generated_at": now(), "files": files})
    write(ATLAS / "source/snapshot.yaml", snapshot_doc)
    print("snapshot", len(files))


def cmd_index(args: argparse.Namespace) -> None:
    files = read(ATLAS / "index/file-index.yaml", {}).get("files", [])
    if not files:
        cmd_snapshot(args)
        files = read(ATLAS / "index/file-index.yaml", {}).get("files", [])
    repo_by_id = {r.id: r for r in repos()}
    collected: dict[str, list[dict[str, Any]]] = {
        "symbols": [], "imports": [], "endpoints": [], "routes": [], "components": [],
        "hooks": [], "api_clients": [], "schemas": [], "services": [], "data_access": [],
        "runtime": [], "ui_actions": [], "tests": [], "configs": [],
    }
    for rec in files:
        repo = repo_by_id.get(rec["repo"])
        path = repo and repo.path / rec["path"]
        if rec["classification"] == "config":
            collected["configs"].append({"id": f"config.{rec['repo']}.{slug(rec['path'])}", "repo": rec["repo"], "file": rec["path"], "language": rec["language"], "confidence": "medium", "needs_review": True})
        if rec["classification"] == "test":
            collected["tests"].append({"id": f"testfile.{rec['repo']}.{slug(rec['path'])}", "repo": rec["repo"], "file": rec["path"], "confidence": "medium", "needs_review": True})
        if not path or rec["language"] not in {"python", "typescript", "typescript-react", "javascript", "javascript-react"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        idx = python_indexes(repo, rec, path, text) if rec["language"] == "python" else ts_indexes(repo, rec, text)
        for key, items in idx.items():
            collected.setdefault(key, []).extend(items)

    output_map = {
        "symbol-index.yaml": ("symbols", collected["symbols"]),
        "import-index.yaml": ("imports", collected["imports"]),
        "endpoint-index.yaml": ("endpoints", collected["endpoints"]),
        "route-index.yaml": ("routes", collected["routes"]),
        "component-index.yaml": ("components", collected["components"]),
        "hook-index.yaml": ("hooks", collected["hooks"]),
        "api-client-index.yaml": ("api_clients", collected["api_clients"]),
        "schema-index.yaml": ("schemas", collected["schemas"]),
        "service-index.yaml": ("services", collected["services"]),
        "data-access-index.yaml": ("data_access", collected["data_access"]),
        "runtime-entrypoint-index.yaml": ("runtime_entrypoints", collected["runtime"]),
        "ui-action-index.yaml": ("ui_actions", collected["ui_actions"]),
        "test-index.yaml": ("tests", collected["tests"]),
        "config-index.yaml": ("configs", collected["configs"]),
    }
    for filename, (key, items) in output_map.items():
        write(ATLAS / "index" / filename, {"generated_at": now(), key: sorted(items, key=lambda x: x.get("id", ""))})
    write(ATLAS / "runtime/runtime-map.yaml", {"generated_at": now(), "runtime_entrypoints": collected["runtime"]})
    write(ATLAS / "testing/test-inventory.yaml", {"generated_at": now(), "tests": collected["tests"]})
    print("index", len(collected["symbols"]), len(collected["endpoints"]), len(collected["routes"]), len(collected["api_clients"]))


def load_collection(filename: str, key: str) -> list[dict[str, Any]]:
    return read(ATLAS / "index" / filename, {}).get(key, [])


def first_annotation_from_signature(signature: str) -> dict[str, Any]:
    """Return lightweight payload hints from a Python signature string.

    The suite intentionally avoids executing application code. These hints are
    deterministic evidence pointers, not complete OpenAPI contracts.
    """
    if "(" not in signature or ")" not in signature:
        return {"parameters": [], "return_annotation": None, "confidence": "low"}
    before_return, _, return_annotation = signature.partition(" -> ")
    params_text = before_return.split("(", 1)[1].rsplit(")", 1)[0].strip()
    params = []
    if params_text:
        for raw in [x.strip() for x in params_text.split(",") if x.strip()]:
            if raw in {"self", "cls", "request"}:
                continue
            name, _, annotation = raw.partition(":")
            params.append({"name": name.strip().lstrip("*"), "annotation": annotation.strip() or None})
    return {"parameters": params, "return_annotation": return_annotation.strip() or None, "confidence": "medium" if params or return_annotation else "low"}


def collection_items() -> dict[str, list[dict[str, Any]]]:
    return {
        "symbols": load_collection("symbol-index.yaml", "symbols"),
        "endpoints": load_collection("endpoint-index.yaml", "endpoints"),
        "routes": load_collection("route-index.yaml", "routes"),
        "api_clients": load_collection("api-client-index.yaml", "api_clients"),
        "schemas": load_collection("schema-index.yaml", "schemas"),
        "services": load_collection("service-index.yaml", "services"),
        "data_access": load_collection("data-access-index.yaml", "data_access"),
        "runtime": load_collection("runtime-entrypoint-index.yaml", "runtime_entrypoints"),
        "tests": load_collection("test-index.yaml", "tests"),
        "configs": load_collection("config-index.yaml", "configs"),
    }


def cmd_semantic_layers(_: argparse.Namespace) -> None:
    """Build deterministic higher-layer seed artifacts from lower indexes.

    These artifacts are deliberately conservative: every assertion is copied
    from deterministic indexes and keeps evidence/review metadata instead of
    inventing business semantics.
    """
    ensure_dirs()
    c = collection_items()
    symbols_by_id = {x.get("id"): x for x in c["symbols"]}
    schemas_by_name = {x.get("name"): x for x in c["schemas"]}

    contracts: list[dict[str, Any]] = []
    for endpoint in c["endpoints"]:
        symbol = symbols_by_id.get(endpoint.get("source_symbol"), {})
        signature_hints = first_annotation_from_signature(str(symbol.get("signature", "")))
        request_schema = None
        for param in signature_hints["parameters"]:
            ann = param.get("annotation")
            if ann and ann in schemas_by_name:
                request_schema = schemas_by_name[ann]["id"]
                break
        contracts.append(
            {
                "id": f"contract.{slug(endpoint.get('id'))}",
                "endpoint": endpoint.get("id"),
                "method": endpoint.get("method"),
                "path": endpoint.get("path"),
                "handler": endpoint.get("handler"),
                "request_parameters": signature_hints["parameters"],
                "request_schema": request_schema,
                "response_schema": schemas_by_name.get(signature_hints.get("return_annotation"), {}).get("id"),
                "status": "seeded_from_signature",
                "confidence": "medium" if request_schema or signature_hints["parameters"] else "low",
                "needs_review": not bool(request_schema),
                "evidence": endpoint.get("evidence", []),
            }
        )
    write(ATLAS / "payloads/api-contracts.yaml", {"generated_at": now(), "api_contracts": contracts})

    error_flows: list[dict[str, Any]] = []
    for endpoint in c["endpoints"]:
        raises = endpoint.get("raises", [])
        if not raises:
            error_flows.append(
                {
                    "id": f"error_flow.{slug(endpoint.get('id'))}.unmapped",
                    "source": endpoint.get("id"),
                    "errors": [],
                    "status": "no_explicit_raise_detected",
                    "confidence": "low",
                    "needs_review": True,
                    "evidence": endpoint.get("evidence", []),
                }
            )
            continue
        for raised in raises:
            error_flows.append(
                {
                    "id": f"error_flow.{slug(endpoint.get('id'))}.{slug(raised)}",
                    "source": endpoint.get("id"),
                    "errors": [raised],
                    "status": "explicit_raise_detected",
                    "confidence": "medium",
                    "needs_review": True,
                    "evidence": endpoint.get("evidence", []),
                }
            )
    write(ATLAS / "errors/error-flow-index.yaml", {"generated_at": now(), "error_flows": error_flows})

    facts: list[dict[str, Any]] = []
    fact_sources = [
        ("endpoint", c["endpoints"], lambda x: f"{x.get('method')} {x.get('path')} is handled by {x.get('handler')}"),
        ("schema", c["schemas"], lambda x: f"schema {x.get('name')} defines {len(x.get('fields', []))} field(s)"),
        ("service", c["services"], lambda x: f"service function {x.get('function')} is indexed"),
        ("data_access", c["data_access"], lambda x: f"data-access function {x.get('function')} is indexed"),
        ("api_client", c["api_clients"], lambda x: f"frontend API client calls {x.get('method')} {x.get('path')}"),
        ("route", c["routes"], lambda x: f"frontend route {x.get('path')} is indexed"),
    ]
    for typ, items, sentence in fact_sources:
        for item in items:
            facts.append(
                {
                    "id": f"fact.{typ}.{slug(item.get('id'))}",
                    "type": typ,
                    "statement": sentence(item),
                    "source_id": item.get("id"),
                    "repo": item.get("repo"),
                    "file": item.get("file"),
                    "confidence": item.get("confidence", "medium"),
                    "needs_review": item.get("needs_review", True),
                    "evidence": item.get("evidence", []),
                }
            )
    write(ATLAS / "facts/technical-facts.yaml", {"generated_at": now(), "technical_facts": facts})

    graph_nodes = read(ATLAS / "graph/nodes.yaml", {}).get("nodes", [])
    graph_edges = read(ATLAS / "graph/edges.yaml", {}).get("edges", [])
    knowledge_nodes = [
        {
            "id": node.get("id"),
            "type": node.get("type"),
            "label": node.get("name") or node.get("id"),
            "repo": node.get("repo"),
            "file": node.get("file"),
            "source": "graph/nodes.yaml",
        }
        for node in graph_nodes
        if node.get("id")
    ]
    write(ATLAS / "knowledge/nodes/normalized-nodes.yaml", {"generated_at": now(), "nodes": knowledge_nodes})
    write(ATLAS / "knowledge/graph/normalized-graph.yaml", {"generated_at": now(), "nodes": knowledge_nodes, "edges": graph_edges})
    write(ATLAS / "knowledge/indexes/id-index.yaml", {"generated_at": now(), "ids": sorted(node["id"] for node in knowledge_nodes)})


def cmd_graph(_: argparse.Namespace) -> None:
    collections = {
        "symbol": load_collection("symbol-index.yaml", "symbols"),
        "endpoint": load_collection("endpoint-index.yaml", "endpoints"),
        "api_client": load_collection("api-client-index.yaml", "api_clients"),
        "route": load_collection("route-index.yaml", "routes"),
        "component": load_collection("component-index.yaml", "components"),
        "hook": load_collection("hook-index.yaml", "hooks"),
        "schema": load_collection("schema-index.yaml", "schemas"),
        "service": load_collection("service-index.yaml", "services"),
        "data_access": load_collection("data-access-index.yaml", "data_access"),
        "runtime": load_collection("runtime-entrypoint-index.yaml", "runtime_entrypoints"),
        "test": load_collection("test-index.yaml", "tests"),
        "config": load_collection("config-index.yaml", "configs"),
    }
    nodes = [
        {"id": item["id"], "type": typ, "repo": item.get("repo"), "file": item.get("file"), "name": item.get("name") or item.get("path") or item.get("function")}
        for typ, items in collections.items() for item in items if item.get("id")
    ]
    ids = {n["id"] for n in nodes}
    symbol_by_name: dict[tuple[str, str], list[str]] = {}
    for symbol in collections["symbol"]:
        symbol_by_name.setdefault((symbol.get("repo"), symbol.get("name")), []).append(symbol["id"])

    edges: list[dict[str, Any]] = []

    def add_edge(source: str | None, target: str | None, typ: str, confidence: str = "medium", evidence: list[dict[str, Any]] | None = None) -> None:
        if not source or not target:
            return
        edges.append({"id": f"edge.{slug(source)}.{typ.lower()}.{slug(target)}", "source": source, "target": target, "type": typ, "confidence": confidence, "needs_review": confidence != "high", "evidence": evidence or []})

    endpoint_contract = {(e.get("method"), e.get("path")): e for e in collections["endpoint"]}
    for endpoint in collections["endpoint"]:
        add_edge(endpoint["id"], endpoint.get("source_symbol"), "IMPLEMENTS", "high", endpoint.get("evidence"))
        for call in endpoint.get("calls", []):
            short = call.split(".")[-1]
            for target in symbol_by_name.get((endpoint.get("repo"), short), []):
                add_edge(endpoint["id"], target, "CALLS", "medium", endpoint.get("evidence"))
    for symbol in collections["symbol"]:
        for call in symbol.get("calls", []):
            short = call.split(".")[-1]
            for target in symbol_by_name.get((symbol.get("repo"), short), []):
                if target != symbol["id"]:
                    add_edge(symbol["id"], target, "CALLS", "medium", symbol.get("evidence"))
    for api in collections["api_client"]:
        matched = endpoint_contract.get((api.get("method"), api.get("path")))
        if matched:
            add_edge(api["id"], matched["id"], "MAPS_TO", "high", api.get("evidence"))
    for schema in collections["schema"]:
        add_edge(schema["id"], schema.get("source_symbol"), "EVIDENCED_BY", "high", schema.get("evidence"))
    for service in collections["service"]:
        add_edge(service["id"], service.get("source_symbol"), "EVIDENCED_BY", "medium", service.get("evidence"))
    for data in collections["data_access"]:
        add_edge(data["id"], data.get("source_symbol"), "EVIDENCED_BY", "medium", data.get("evidence"))
    for test in collections["test"]:
        if test.get("source_symbol"):
            add_edge(test["id"], test.get("source_symbol"), "EVIDENCED_BY", "medium", test.get("evidence"))

    write(ATLAS / "graph/nodes.yaml", {"generated_at": now(), "nodes": sorted(nodes, key=lambda x: x["id"])})
    write(ATLAS / "graph/edges.yaml", {"generated_at": now(), "edges": sorted(edges, key=lambda x: x["id"])})
    build_flows(collections, edges)
    print("graph", len(nodes), len(edges))


def runtime_envelope_for(endpoint: dict[str, Any], runtime_items: list[dict[str, Any]]) -> dict[str, Any]:
    repo = endpoint.get("repo")
    before = [x["id"] for x in runtime_items if x.get("repo") == repo and x.get("type") in {"middleware", "middleware_registration", "dependency"}]
    errors = [x["id"] for x in runtime_items if x.get("repo") == repo and "exception" in str(x.get("type"))]
    return {"before_endpoint": before[:20], "after_endpoint": [], "exception_path": errors[:20], "needs_runtime_review": bool(before or errors)}


def build_flows(collections: dict[str, list[dict[str, Any]]], edges: list[dict[str, Any]]) -> None:
    api_flows: list[dict[str, Any]] = []
    ui_flows: list[dict[str, Any]] = []
    edges_by_source: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        edges_by_source.setdefault(edge["source"], []).append(edge)
    for endpoint in collections["endpoint"]:
        steps = [
            {"order": 1, "type": "receive_request", "node": endpoint["id"]},
            {"order": 2, "type": "handler", "node": endpoint.get("source_symbol")},
        ]
        order = 3
        for edge in edges_by_source.get(endpoint["id"], []):
            if edge["type"] == "CALLS":
                steps.append({"order": order, "type": "call", "node": edge["target"]})
                order += 1
        api_flows.append(
            {
                "id": f"flow.api.{slug(endpoint['id'])}",
                "trigger": {"method": endpoint.get("method"), "path": endpoint.get("path"), "endpoint": endpoint["id"]},
                "runtime_envelope": runtime_envelope_for(endpoint, collections["runtime"]),
                "steps": steps,
                "branches": endpoint.get("branches", []),
                "error_exits": [{"raises": r, "confidence": "medium", "needs_review": True} for r in endpoint.get("raises", [])],
                "confidence": "medium",
                "needs_review": True,
                "evidence": endpoint.get("evidence", []),
            }
        )
    apis_by_file: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for api in collections["api_client"]:
        apis_by_file.setdefault((api.get("repo"), api.get("file")), []).append(api)
    for route in collections["route"]:
        route_apis = apis_by_file.get((route.get("repo"), route.get("file")), [])
        steps = [{"order": 1, "type": "navigate", "node": route["id"]}]
        for index, api in enumerate(route_apis, start=2):
            steps.append({"order": index, "type": "api_call", "node": api["id"]})
        ui_flows.append({"id": f"flow.ui.{slug(route['id'])}", "route": route["id"], "steps": steps, "states": ["initial", "loading", "success", "error"], "confidence": "low" if not route_apis else "medium", "needs_review": True, "evidence": route.get("evidence", [])})
    write(ATLAS / "flows/api-request-flows.yaml", {"generated_at": now(), "api_request_flows": api_flows})
    write(ATLAS / "flows/ui-flows.yaml", {"generated_at": now(), "ui_flows": ui_flows})


def cmd_validate(_: argparse.Namespace) -> None:
    findings: list[dict[str, Any]] = []
    required_artifacts = [
        "source/snapshot.yaml",
        "index/file-index.yaml",
        "graph/nodes.yaml",
        "graph/edges.yaml",
        "payloads/api-contracts.yaml",
        "errors/error-flow-index.yaml",
        "facts/technical-facts.yaml",
        "knowledge/graph/normalized-graph.yaml",
    ]
    for rel in required_artifacts:
        if not (ATLAS / rel).exists():
            findings.append({"type": "missing_required_artifact", "path": f"atlas/{rel}"})
    nodes = read(ATLAS / "graph/nodes.yaml", {}).get("nodes", [])
    ids = {node.get("id") for node in nodes}
    for edge in read(ATLAS / "graph/edges.yaml", {}).get("edges", []):
        if edge.get("source") not in ids:
            findings.append({"type": "broken_source", "edge": edge.get("id"), "source": edge.get("source")})
        if edge.get("target") not in ids:
            findings.append({"type": "broken_target", "edge": edge.get("id"), "target": edge.get("target")})
    for node in nodes:
        if not node.get("id"):
            findings.append({"type": "missing_node_id", "node": node})
    for flow_file, key in [("api-request-flows.yaml", "api_request_flows"), ("ui-flows.yaml", "ui_flows")]:
        for flow in read(ATLAS / "flows" / flow_file, {}).get(key, []):
            for step in flow.get("steps", []):
                if step.get("node") and step.get("node") not in ids:
                    findings.append({"type": "flow_step_unknown_node", "flow": flow.get("id"), "node": step.get("node")})
    write(ATLAS / "audit/v2-validation-report.yaml", {"generated_at": now(), "status": "ok" if not findings else "needs_review", "finding_count": len(findings), "findings": findings})
    print("validate", len(findings))


def cmd_drift(_: argparse.Namespace) -> None:
    old_files = read(ATLAS / "source/file-hashes.yaml", {}).get("files", [])
    old = {f"{x['repo']}:{x['path']}": x for x in old_files}
    current_files, _ = scan_files()
    current = {f"{x['repo']}:{x['path']}": x for x in current_files}
    changed = [{"repo": current[k]["repo"], "path": current[k]["path"], "old_sha256": old[k]["sha256"], "new_sha256": current[k]["sha256"]} for k in sorted(current.keys() & old.keys()) if current[k]["sha256"] != old[k]["sha256"]]
    added = [current[k] for k in sorted(current.keys() - old.keys())]
    removed = [old[k] for k in sorted(old.keys() - current.keys())]
    changed_paths = {(x["repo"], x["path"]) for x in changed + added + removed}
    impacted_nodes = [node for node in read(ATLAS / "graph/nodes.yaml", {}).get("nodes", []) if (node.get("repo"), node.get("file")) in changed_paths]
    impacted_ids = {node.get("id") for node in impacted_nodes}
    impacted_edges = [edge for edge in read(ATLAS / "graph/edges.yaml", {}).get("edges", []) if edge.get("source") in impacted_ids or edge.get("target") in impacted_ids]
    write(ATLAS / "change/changed-files.yaml", {"generated_at": now(), "changed": changed, "added": added, "removed": removed})
    write(ATLAS / "change/impacted-nodes.yaml", {"generated_at": now(), "impacted_nodes": impacted_nodes})
    write(ATLAS / "change/impacted-edges.yaml", {"generated_at": now(), "impacted_edges": impacted_edges})
    write(ATLAS / "change/targeted-rerun-plan.yaml", {"generated_at": now(), "recommended_steps": ["snapshot", "index", "graph", "validate"], "reason": "changed files detected" if changed or added or removed else "no file hash drift detected"})
    print("drift", len(changed), "changed", len(added), "added", len(removed), "removed")


def cmd_visualizer(_: argparse.Namespace) -> None:
    nodes = read(ATLAS / "graph/nodes.yaml", {}).get("nodes", [])
    edges = read(ATLAS / "graph/edges.yaml", {}).get("edges", [])
    api_flows = read(ATLAS / "flows/api-request-flows.yaml", {}).get("api_request_flows", [])
    ui_flows = read(ATLAS / "flows/ui-flows.yaml", {}).get("ui_flows", [])
    node_detail = {node["id"]: node for node in nodes if node.get("id")}
    write(ATLAS / "visualizer/graph-data.json", {"generated_at": now(), "nodes": nodes, "edges": edges, "api_flows": api_flows, "ui_flows": ui_flows})
    write(ATLAS / "visualizer/cytoscape-elements.json", {"elements": [{"data": x} for x in nodes + edges]})
    write(ATLAS / "visualizer/node-detail-index.json", node_detail)
    write(ATLAS / "visualizer/flow-cards.json", {"api_flows": api_flows, "ui_flows": ui_flows})
    print("visualizer", len(nodes), len(edges), len(api_flows), len(ui_flows))


def cmd_all(args: argparse.Namespace) -> None:
    for fn in [cmd_init, cmd_snapshot, cmd_index, cmd_graph, cmd_semantic_layers, cmd_validate, cmd_visualizer]:
        fn(args)


def main() -> None:
    parser = argparse.ArgumentParser(description="CodeAtlas V2 deterministic foundation suite")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ["init", "snapshot", "index", "graph", "semantic-layers", "validate", "drift-check", "visualizer-export", "all"]:
        sub.add_parser(name)
    args = parser.parse_args()
    {
        "init": cmd_init,
        "snapshot": cmd_snapshot,
        "index": cmd_index,
        "graph": cmd_graph,
        "semantic-layers": cmd_semantic_layers,
        "validate": cmd_validate,
        "drift-check": cmd_drift,
        "visualizer-export": cmd_visualizer,
        "all": cmd_all,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
