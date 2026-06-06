# Graphify Patterns Adopted

CodeAtlas should not become a generic project graph tool. Graphify is useful as a reference because it has a simple query-first developer workflow, portable graph outputs, and graph reports that make large repositories easier to inspect.

CodeAtlas keeps a narrower purpose: deterministic, typed reverse engineering for FastAPI, React/TypeScript, OpenSearch, Kiro, and `ngk`.

## Adopted in this repo

| Pattern | CodeAtlas implementation |
|---|---|
| Query-first graph usage | `atlas/tools/codeatlas_query.py` provides `query`, `explain`, and `path` commands over deterministic Atlas artifacts. |
| Portable graph export | `atlas/tools/codeatlas_graph_report.py` writes `atlas/visualizer/graph.json`. |
| Human-readable graph report | `atlas/tools/codeatlas_graph_report.py` writes `atlas/visualizer/GRAPH_REPORT.md` and `graph-report.json`. |
| Offline graph browser | `atlas/tools/codeatlas_graph_html.py` writes `atlas/visualizer/graph.html` from `graph.json`. |
| Hub and orphan visibility | The report highlights high-degree nodes and disconnected nodes. |
| Confidence visibility | The report summarizes edge confidence counts. |
| Deterministic artifact validation | `atlas/tools/validate_artifacts.py` parses generated artifacts and checks graph/flow links. |
| Generated-output safety | `.gitignore` ignores generated Atlas artifacts and local read models by default. |
| JSON-first trace loading | `ngk_trace_regraph_exporter.py` prefers `.json` artifacts and falls back to legacy `.yaml`. |
| Canonical runner integration | `codeatlas_v2_canonical.py all` runs graph reporting and artifact validation after the deterministic suite. |

## Partially adopted / still to wire

| Pattern | Current status |
|---|---|
| JSON-first artifact generation everywhere | The wrapper promotes JSON-compatible `.yaml` outputs to `.json`, but the legacy V2 suite still writes `.yaml` internally. |
| Ignore-file scanner support | Built-in ignore directories exist; `.codeatlasignore` support is still future work. |
| Single wrapper for every helper command | Some helper commands are still invoked directly by scripts instead of through `codeatlas_v2_canonical.py`. |

## Not adopted now

| Graphify idea | Reason |
|---|---|
| Generic multimodal ingestion | CodeAtlas should first harden typed app extraction. |
| Broad assistant skill layer | Kiro and `ngk` should consume deterministic Atlas artifacts first. |
| Committing generated graph output by default | Atlas artifacts can expose private code knowledge and are ignored by default. |

## Commands

```bash
python3 atlas/tools/codeatlas_v2_canonical.py all
python3 atlas/tools/codeatlas_v2_canonical.py graph-report
python3 atlas/tools/codeatlas_v2_canonical.py validate-artifacts
python3 atlas/tools/codeatlas_graph_html.py
python3 atlas/tools/codeatlas_query.py query "claims endpoint"
python3 atlas/tools/codeatlas_query.py explain "POST /claims"
python3 atlas/tools/codeatlas_query.py path "claims route" "claims endpoint"
```

## Remaining follow-up

- Rename V2 suite writers from `.yaml` to `.json` once all downstream readers use canonical JSON paths.
- Add `.codeatlasignore` scanner support if the built-in ignore rules are not enough.
- Add SQLite read-model loading when `ngk ask/review/trace` needs fast structured queries.
