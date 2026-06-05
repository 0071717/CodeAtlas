#!/usr/bin/env python3
"""CodeAtlas V2 deterministic foundation suite.

Fast, dependency-light tooling for source snapshots, file/symbol indexes,
graph/flow seeds, drift reports, validation reports, and visualizer exports.
Outputs are JSON, which is valid YAML and deterministic for Kiro/tools.
"""
from __future__ import annotations

import argparse, ast, hashlib, json, os, re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()
ATLAS = ROOT / "atlas"
CONFIG = ATLAS / "config" / "project.yaml"
IGNORE = {".git", "node_modules", "dist", "build", "coverage", ".venv", "venv", "__pycache__", ".next", ".cache"}
SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx"}
HTTP = {"get", "post", "put", "patch", "delete", "options", "head"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: object) -> str:
    text = str(value).replace("\\", "/").strip("/")
    text = re.sub(r"[^A-Za-z0-9_./-]+", "_", text).replace("/", ".").replace("-", "_")
    return re.sub(r"\.+", ".", text).strip(".") or "root"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def read(path: Path, default: object) -> object:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def ensure_dirs() -> None:
    for rel in "source index graph flows audit change visualizer testing knowledge/nodes knowledge/indexes knowledge/graph knowledge/cards".split():
        (ATLAS / rel).mkdir(parents=True, exist_ok=True)


def repos() -> list[dict]:
    if not CONFIG.exists():
        return []
    out: list[dict] = []
    current: dict | None = None
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
    return [repo for repo in out if repo.get("path")]


def classify(path: str) -> tuple[str, str]:
    ext = Path(path).suffix.lower()
    language = {".py": "python", ".ts": "typescript", ".tsx": "typescript-react", ".js": "javascript", ".jsx": "javascript-react", ".yaml": "yaml", ".yml": "yaml", ".json": "json", ".md": "markdown"}.get(ext, "unknown")
    low = path.lower()
    if any(token in low for token in ["/test/", "/tests/", ".spec.", ".test."]):
        kind = "test"
    elif ext in SOURCE_EXTS:
        kind = "source"
    elif ext in {".yaml", ".yml", ".json"}:
        kind = "config"
    elif ext == ".md":
        kind = "documentation"
    else:
        kind = "asset"
    return language, kind


def scan_files() -> tuple[list[dict], list[dict]]:
    files: list[dict] = []
    missing: list[dict] = []
    for repo in repos():
        if not repo["path"].exists():
            missing.append({"repo": repo["id"], "path": str(repo["path"]), "reason": "missing repo"})
            continue
        for root, dirs, names in os.walk(repo["path"]):
            dirs[:] = [d for d in dirs if d not in IGNORE]
            for name in names:
                path = Path(root) / name
                if any(part in IGNORE for part in path.parts):
                    continue
                try:
                    data = path.read_bytes()
                except Exception as exc:
                    missing.append({"repo": repo["id"], "path": str(path), "reason": str(exc)})
                    continue
                rel = str(path.relative_to(repo["path"])).replace("\\", "/")
                language, kind = classify(rel)
                files.append({"id": f"file.{repo['id']}.{slug(rel)}", "repo": repo["id"], "repo_role": repo["role"], "path": rel, "language": language, "classification": kind, "line_count": data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0), "size_bytes": len(data), "sha256": sha256(data)})
    return sorted(files, key=lambda x: (x["repo"], x["path"])), missing


def cmd_init(_: argparse.Namespace) -> None:
    ensure_dirs()
    write(ATLAS / "audit/v2-init-report.yaml", {"generated_at": now(), "status": "ok"})
    print("init")


def cmd_snapshot(_: argparse.Namespace) -> None:
    ensure_dirs()
    files, missing = scan_files()
    write(ATLAS / "source/file-hashes.yaml", {"generated_at": now(), "files": files})
    write(ATLAS / "index/file-index.yaml", {"generated_at": now(), "files": files})
    write(ATLAS / "source/snapshot.yaml", {"generated_at": now(), "repositories": [{"id": r["id"], "path": str(r["path"]), "role": r["role"], "exists": r["path"].exists()} for r in repos()], "file_count": len(files), "missing": missing})
    print("snapshot", len(files))


def call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{call_name(node.value)}.{node.attr}".strip(".")
    if isinstance(node, ast.Call):
        return call_name(node.func)
    return ""


def cmd_index(args: argparse.Namespace) -> None:
    files = read(ATLAS / "index/file-index.yaml", {}).get("files", [])  # type: ignore[union-attr]
    if not files:
        cmd_snapshot(args)
        files = read(ATLAS / "index/file-index.yaml", {}).get("files", [])  # type: ignore[union-attr]
    repo_by_id = {r["id"]: r for r in repos()}
    symbols: list[dict] = []
    endpoints: list[dict] = []
    routes: list[dict] = []
    api_clients: list[dict] = []
    tests: list[dict] = []
    for rec in files:
        repo = repo_by_id.get(rec["repo"])
        path = repo and repo["path"] / rec["path"]
        if rec["classification"] == "test":
            tests.append({"id": f"testfile.{rec['repo']}.{slug(rec['path'])}", "repo": rec["repo"], "file": rec["path"], "confidence": "medium", "needs_review": True})
        if not path or rec["language"] not in {"python", "typescript", "typescript-react", "javascript", "javascript-react"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if rec["language"] == "python":
            try:
                tree = ast.parse(text)
            except Exception:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    start = getattr(node, "lineno", 1)
                    end = getattr(node, "end_lineno", start)
                    symbol_id = f"symbol.{rec['repo']}.{slug(Path(rec['path']).with_suffix('').as_posix())}.{node.name}"
                    calls = sorted({call_name(c.func) for c in ast.walk(node) if isinstance(c, ast.Call) and call_name(c.func)})[:100]
                    evidence = [{"type": "code", "repo": rec["repo"], "file": rec["path"], "symbol": node.name, "line_start": start, "line_end": end}]
                    symbols.append({"id": symbol_id, "repo": rec["repo"], "file": rec["path"], "name": node.name, "kind": "class" if isinstance(node, ast.ClassDef) else "function", "line_start": start, "line_end": end, "calls": calls, "evidence": evidence})
                    for dec in getattr(node, "decorator_list", []):
                        if isinstance(dec, ast.Call) and call_name(dec.func).split(".")[-1].lower() in HTTP:
                            method = call_name(dec.func).split(".")[-1].upper()
                            route_path = dec.args[0].value if dec.args and hasattr(dec.args[0], "value") else None
                            endpoints.append({"id": f"endpoint.{rec['repo']}.{slug(method + '.' + str(route_path or node.name))}", "repo": rec["repo"], "file": rec["path"], "method": method, "path": route_path, "handler": node.name, "source_symbol": symbol_id, "calls": calls, "confidence": "high" if route_path else "medium", "needs_review": route_path is None, "evidence": evidence})
        else:
            for match in re.finditer(r"(?:export\s+)?(?:function|const|class)\s+([A-Z_a-z][A-Za-z0-9_]*)", text):
                name = match.group(1)
                line = text.count("\n", 0, match.start()) + 1
                symbols.append({"id": f"symbol.{rec['repo']}.{slug(Path(rec['path']).with_suffix('').as_posix())}.{name}", "repo": rec["repo"], "file": rec["path"], "name": name, "line_start": line, "line_end": line})
            for match in re.finditer(r"<Route[^>]+path=[{\"']+([^}\"']+)", text):
                routes.append({"id": f"route.{rec['repo']}.{slug(match.group(1))}", "repo": rec["repo"], "file": rec["path"], "path": match.group(1), "confidence": "medium", "needs_review": True})
            for match in re.finditer(r"(fetch|axios\.[a-z]+|client\.[a-z]+)\s*\(\s*([`\"'])([^`\"']+)\2", text, re.I):
                method = match.group(1).split(".")[-1].upper() if "." in match.group(1) else "UNKNOWN"
                api_clients.append({"id": f"api.{rec['repo']}.{slug(rec['path'])}.{slug(match.group(3))}", "repo": rec["repo"], "file": rec["path"], "method": method, "path": match.group(3), "confidence": "medium", "needs_review": True})
    for filename, key, data in [("symbol-index.yaml", "symbols", symbols), ("endpoint-index.yaml", "endpoints", endpoints), ("route-index.yaml", "routes", routes), ("api-client-index.yaml", "api_clients", api_clients), ("test-index.yaml", "tests", tests)]:
        write(ATLAS / "index" / filename, {"generated_at": now(), key: data})
    print("index", len(symbols), len(endpoints), len(routes), len(api_clients))


def cmd_graph(_: argparse.Namespace) -> None:
    endpoints = read(ATLAS / "index/endpoint-index.yaml", {}).get("endpoints", [])  # type: ignore[union-attr]
    apis = read(ATLAS / "index/api-client-index.yaml", {}).get("api_clients", [])  # type: ignore[union-attr]
    symbols = read(ATLAS / "index/symbol-index.yaml", {}).get("symbols", [])  # type: ignore[union-attr]
    nodes = [{"id": x["id"], "type": typ, "repo": x.get("repo"), "file": x.get("file"), "name": x.get("name") or x.get("path")} for typ, col in [("symbol", symbols), ("endpoint", endpoints), ("api_client", apis)] for x in col]
    ids = {x["id"] for x in nodes}
    edges: list[dict] = []
    def edge(source: str, target: str, typ: str, confidence: str = "medium") -> None:
        edges.append({"id": f"edge.{slug(source)}.{typ.lower()}.{slug(target)}", "source": source, "target": target, "type": typ, "confidence": confidence, "needs_review": confidence != "high"})
    by_contract = {(e.get("method"), e.get("path")): e for e in endpoints}
    for endpoint in endpoints:
        if endpoint.get("source_symbol") in ids:
            edge(endpoint["id"], endpoint["source_symbol"], "IMPLEMENTS", "high")
    for api in apis:
        matched = by_contract.get((api.get("method"), api.get("path")))
        if matched:
            edge(api["id"], matched["id"], "MAPS_TO", "high")
    write(ATLAS / "graph/nodes.yaml", {"generated_at": now(), "nodes": nodes})
    write(ATLAS / "graph/edges.yaml", {"generated_at": now(), "edges": edges})
    write(ATLAS / "flows/api-request-flows.yaml", {"generated_at": now(), "api_request_flows": [{"id": f"flow.api.{slug(e['id'])}", "trigger": {"method": e.get("method"), "path": e.get("path"), "endpoint": e["id"]}, "steps": [{"order": 1, "type": "receive_request", "node": e["id"]}, {"order": 2, "type": "handler", "node": e.get("source_symbol")}], "confidence": "medium", "needs_review": True} for e in endpoints]})
    print("graph", len(nodes), len(edges))


def cmd_validate(_: argparse.Namespace) -> None:
    findings: list[dict] = []
    ids = {x.get("id") for x in read(ATLAS / "graph/nodes.yaml", {}).get("nodes", [])}  # type: ignore[union-attr]
    for e in read(ATLAS / "graph/edges.yaml", {}).get("edges", []):  # type: ignore[union-attr]
        if e.get("source") not in ids:
            findings.append({"type": "broken_source", "edge": e.get("id")})
        if e.get("target") not in ids:
            findings.append({"type": "broken_target", "edge": e.get("id")})
    write(ATLAS / "audit/v2-validation-report.yaml", {"generated_at": now(), "status": "ok" if not findings else "needs_review", "findings": findings})
    print("validate", len(findings))


def cmd_drift(_: argparse.Namespace) -> None:
    old = {f"{x['repo']}:{x['path']}": x for x in read(ATLAS / "source/file-hashes.yaml", {}).get("files", [])}  # type: ignore[union-attr]
    current = {f"{x['repo']}:{x['path']}": x for x in scan_files()[0]}
    changed = [{"repo": current[k]["repo"], "path": current[k]["path"]} for k in current.keys() & old.keys() if current[k]["sha256"] != old[k]["sha256"]]
    write(ATLAS / "change/changed-files.yaml", {"generated_at": now(), "changed": changed, "added": [current[k] for k in current.keys() - old.keys()], "removed": [old[k] for k in old.keys() - current.keys()]})
    print("drift", len(changed))


def cmd_visualizer(_: argparse.Namespace) -> None:
    nodes = read(ATLAS / "graph/nodes.yaml", {}).get("nodes", [])  # type: ignore[union-attr]
    edges = read(ATLAS / "graph/edges.yaml", {}).get("edges", [])  # type: ignore[union-attr]
    write(ATLAS / "visualizer/graph-data.json", {"generated_at": now(), "nodes": nodes, "edges": edges})
    write(ATLAS / "visualizer/cytoscape-elements.json", {"elements": [{"data": x} for x in nodes + edges]})
    print("visualizer", len(nodes), len(edges))


def cmd_all(args: argparse.Namespace) -> None:
    for fn in [cmd_init, cmd_snapshot, cmd_index, cmd_graph, cmd_validate, cmd_visualizer]:
        fn(args)


def main() -> None:
    parser = argparse.ArgumentParser(description="CodeAtlas V2 deterministic foundation suite")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ["init", "snapshot", "index", "graph", "validate", "drift-check", "visualizer-export", "all"]:
        sub.add_parser(name)
    args = parser.parse_args()
    {"init": cmd_init, "snapshot": cmd_snapshot, "index": cmd_index, "graph": cmd_graph, "validate": cmd_validate, "drift-check": cmd_drift, "visualizer-export": cmd_visualizer, "all": cmd_all}[args.cmd](args)


if __name__ == "__main__":
    main()
