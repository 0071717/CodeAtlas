"""Phase 7 acceptance tests: FastAPI AST extraction (hermetic, no app execution).

Drives the real `codeatlas_v2_suite.py index` command against a temp FastAPI app
and asserts the upgraded extraction: response_model / status_code / tags /
dependencies, signature Depends linkage, APIRouter + include_router prefix
composition, add_api_route, add_exception_handler, and BackgroundTasks.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SUITE = REPO / "atlas" / "tools" / "codeatlas_v2_suite.py"

APP = '''\
from fastapi import FastAPI, APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel

app = FastAPI()
router = APIRouter(prefix="/properties")


def get_db():
    return None


def get_current_user():
    return None


class SearchResult(BaseModel):
    location: str


@router.get("/search", response_model=SearchResult, status_code=200, tags=["search"], dependencies=[Depends(get_db)])
def search(q: str, bg: BackgroundTasks, user=Depends(get_current_user)):
    return []


def health():
    return {"ok": True}


def on_error(request, exc):
    return None


def notify(bg: BackgroundTasks):
    return None


app.include_router(router, prefix="/api/v1")
app.add_api_route("/health", health, methods=["GET"])
app.add_exception_handler(ValueError, on_error)
'''


def build_and_index(project: Path) -> None:
    (project / "atlas" / "config").mkdir(parents=True)
    (project / "atlas" / "config" / "project.yaml").write_text(
        "project: testproj\nrepositories:\n  api:\n    path: api\n    role: backend\n    language: python\n",
        encoding="utf-8",
    )
    (project / "api").mkdir()
    (project / "api" / "main.py").write_text(APP, encoding="utf-8")
    proc = subprocess.run([sys.executable, str(SUITE), "index"], cwd=project, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


def load(project: Path, stem: str) -> dict:
    return json.loads((project / "atlas" / stem).read_text())


def test_decorator_endpoint_captures_kwargs_and_dependencies(tmp_path):
    build_and_index(tmp_path)
    endpoints = load(tmp_path, "index/endpoint-index.yaml")["endpoints"]
    search = next(e for e in endpoints if e.get("handler") == "search")
    assert search["method"] == "GET"
    assert search["path"] == "/search"
    assert search["response_model"] == "SearchResult"
    assert search["status_code"] == 200
    assert search["tags"] == ["search"]
    assert set(search["dependencies"]) == {"get_db", "get_current_user"}
    assert search["decorator_object"] == "router"
    assert search["uses_background_tasks"] is True


def test_router_and_app_prefixes_compose_full_path(tmp_path):
    build_and_index(tmp_path)
    endpoints = load(tmp_path, "index/endpoint-index.yaml")["endpoints"]
    search = next(e for e in endpoints if e.get("handler") == "search")
    assert search["router_prefix"] == "/properties"
    assert search["app_prefix"] == "/api/v1"
    assert search["full_path"] == "/api/v1/properties/search"
    assert search["path_resolution"] == "app_included_inferred"
    # Composed (not materialised) paths must not silently look authoritative.
    assert search["needs_review"] is True


def test_add_api_route_is_detected(tmp_path):
    build_and_index(tmp_path)
    endpoints = load(tmp_path, "index/endpoint-index.yaml")["endpoints"]
    health = next(e for e in endpoints if e.get("handler") == "health")
    assert health["method"] == "GET"
    assert health["path"] == "/health"
    assert health["programmatic"] is True


def test_add_exception_handler_is_detected(tmp_path):
    build_and_index(tmp_path)
    runtime = load(tmp_path, "index/runtime-entrypoint-index.yaml")["runtime_entrypoints"]
    assert any(r.get("type") == "exception_handler_registration" for r in runtime)


def test_router_index_records_prefix_and_include(tmp_path):
    build_and_index(tmp_path)
    doc = load(tmp_path, "index/fastapi-router-index.yaml")
    assert any(r["var"] == "router" and r["prefix"] == "/properties" for r in doc["routers"])
    assert any(inc["included"] == "router" and inc["prefix"] == "/api/v1" for inc in doc["router_includes"])
