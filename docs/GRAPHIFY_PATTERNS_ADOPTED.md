# Graphify Patterns Adopted

CodeAtlas should not become a generic project graph tool. Graphify is useful as a reference because it has a simple query-first developer workflow, portable graph outputs, and graph reports that make large repositories easier to inspect.

CodeAtlas keeps a narrower purpose: deterministic, typed reverse engineering for FastAPI, React/TypeScript, OpenSearch, Kiro, and `ngk`.

## Adopted in this repo

| Pattern | CodeAtlas implementation |
|---|---|
| Query-first graph usage | `atlas/tools/codeatlas_query.py` provides `query`, `explain`, and `path` commands over deterministic Atlas artifacts. |
| Portable graph export | `atlas/tools/codeatlas_graph_report.py` writes `atlas/visualizer/graph.json`. |
| Human-readable graph report | `atlas/tools/codeatlas_graph_report.py` writes `atlas/visualizer/GRAPH_REPORT.md` and `graph-report.json`. |
| Hub and orphan visibility | The report highlights high-degree nodes and disconnected nodes. |
| Confidence visibility | The report summarizes edge confidence counts. |
| Generated-output safety | `.gitignore` now ignores generated project-knowledge artifacts by default. |
| JSON-first artifact loading | The trace exporter now prefers `.json` and falls back to legacy `.yaml`. |

## Not adopted now

| Graphify idea | Reason |
|---|---|
| Generic multimodal ingestion | CodeAtlas should first harden typed app extraction. |
| MCP serving | The target environment is filesystem-first and MCP is disabled. |
| Broad assistant skill layer | Kiro and `ngk` should consume deterministic Atlas artifacts first. |
| Committing generated graph output by default | Atlas artifacts can expose private code knowledge and are ignored by default. |

## Commands

```bash
python3 atlas/tools/codeatlas_graph_report.py
python3 atlas/tools/codeatlas_query.py query "claims endpoint"
python3 atlas/tools/codeatlas_query.py explain "POST /claims"
python3 atlas/tools/codeatlas_query.py path "claims route" "claims endpoint"
```

## Remaining follow-up

- Wire graph-report into the canonical runner after the V2 suite stabilizes.
- Add a small static HTML graph viewer only after trace bundles are more trustworthy.
- Add `.codeatlasignore` scanner support if the built-in ignore rules are not enough.
- Add SQLite read-model loading when `ngk ask/review/trace` needs fast structured queries.
