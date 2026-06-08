"""Phase 7 acceptance tests: OpenSearch Query DSL reconstruction (Python AST).

A literal query body is reconstructed exactly; a dynamically-built body is kept
as source text and marked unresolved so it is never treated as a complete query.
The artifact is written where ngk_trace expects it (payloads/opensearch-query-dsl).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SUITE = REPO / "atlas" / "tools" / "codeatlas_v2_suite.py"

SERVICE = '''\
from opensearchpy import OpenSearch

client = OpenSearch()


def search_properties(location):
    return client.search(index="properties", body={"query": {"match": {"location": "x"}}})


def dynamic_search(q):
    return client.search(index="properties", body=build_body(q))
'''

# A file that does NOT import opensearch must not produce false positives.
DECOY = '''\
def search(self, q):
    return self.db.search(q)
'''


def build_and_index(project: Path) -> None:
    (project / "atlas" / "config").mkdir(parents=True)
    (project / "atlas" / "config" / "project.yaml").write_text(
        "project: testproj\nrepositories:\n  api:\n    path: api\n    role: backend\n    language: python\n",
        encoding="utf-8",
    )
    (project / "api").mkdir()
    (project / "api" / "search_service.py").write_text(SERVICE, encoding="utf-8")
    (project / "api" / "other.py").write_text(DECOY, encoding="utf-8")
    proc = subprocess.run([sys.executable, str(SUITE), "index"], cwd=project, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


def test_opensearch_dsl_reconstructed_and_unresolved_flagged(tmp_path):
    build_and_index(tmp_path)
    queries = json.loads((tmp_path / "atlas" / "payloads" / "opensearch-query-dsl.yaml").read_text())["queries"]
    by_line = {q["unresolved"]: q for q in queries}

    # Only the two opensearch calls in search_service.py, none from other.py.
    assert len(queries) == 2
    assert all(q["file"] == "search_service.py" for q in queries)

    literal = by_line[False]
    assert literal["index"] == "properties"
    assert literal["query_dsl"] == {"query": {"match": {"location": "x"}}}
    assert literal["needs_review"] is False

    dynamic = by_line[True]
    assert dynamic["unresolved"] is True
    assert "build_body(q)" in str(dynamic["query_dsl"])
    assert dynamic["needs_review"] is True
