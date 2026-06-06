# Graphify Strategy Adoption

CodeAtlas adopts useful workflow patterns from Graphify without becoming a generic graph-memory tool.

## Adopted ideas

| Graphify-style idea | CodeAtlas implementation |
|---|---|
| One graph bundle | `atlas/visualizer/graph.json` |
| Human-readable graph report | `atlas/visualizer/GRAPH_REPORT.md` |
| Browser-openable graph | `atlas/visualizer/graph.html` |
| Query/path/explain workflow | `atlas/tools/codeatlas_query.py` |
| Validation before use | `atlas/tools/codeatlas_artifact_validator.py` and `codeatlas_v2_suite.py validate` |
| Update/check-update loop | `codeatlas_v2_canonical.py drift-check` and `codeatlas_v2_canonical.py update` when available |
| Privacy by default | generated artifacts are ignored and validator scans for obvious secrets |

## Non-goals

CodeAtlas is not trying to become a generic graph memory system for every file, document, image, video, or paper.

CodeAtlas remains a deterministic-first, framework-aware reverse-engineering tool for:

```text
React / TypeScript
FastAPI / Pydantic
OpenSearch / data access
multi-repo config and schema repositories
ngk ask / review / trace
Kiro in a filesystem-only, MCP-disabled environment
```

## Canonical truth boundary

Graph/report/query outputs are **derived read models**.

Canonical truth remains typed CodeAtlas artifacts under:

```text
atlas/source/
atlas/index/
atlas/payloads/
atlas/runtime/
atlas/graph/
atlas/flows/
atlas/testing/
atlas/audit/
atlas/change/
```

AI-derived artifacts remain derived and challengeable. They must not replace deterministic evidence.

## Practical commands

```bash
python3 atlas/tools/codeatlas_v2_canonical.py all
python3 atlas/tools/codeatlas_artifact_validator.py
python3 atlas/tools/codeatlas_graph_report.py
python3 atlas/tools/codeatlas_graph_html.py
python3 atlas/tools/codeatlas_query.py query "main endpoints"
```

## Design rule

Use Graphify-style navigation and reporting to make CodeAtlas easier to consume. Do not let a generic graph abstraction flatten CodeAtlas' typed FastAPI, React, OpenSearch, test, drift, and trace packets.
