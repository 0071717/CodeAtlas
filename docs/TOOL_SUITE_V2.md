# CodeAtlas V2 Deterministic Tool Suite

This guide describes the deterministic tools added for CodeAtlas V2.

The suite is intentionally readable, dependency-light, and fast. It creates the foundation Kiro can inspect and improve without repeatedly asking an AI to rescan the whole project.

## Canonical command

Use the canonical wrapper:

```bash
python3 atlas/tools/codeatlas_v2_canonical.py all
```

The wrapper runs the deterministic suite and promotes JSON-compatible legacy `.yaml` outputs to canonical `.json` outputs.

You may also run:

```bash
python3 atlas/tools/codeatlas_v2_canonical.py doctor
python3 atlas/tools/codeatlas_v2_canonical.py snapshot
python3 atlas/tools/codeatlas_v2_canonical.py index
python3 atlas/tools/codeatlas_v2_canonical.py graph
python3 atlas/tools/codeatlas_v2_canonical.py validate
python3 atlas/tools/codeatlas_v2_canonical.py drift-check
python3 atlas/tools/codeatlas_v2_canonical.py visualizer-export
python3 atlas/tools/codeatlas_v2_canonical.py promote-json
```

Runner:

```bash
bash atlas/scripts/run-framework-v2-suite.sh
```

## Canonical foundation outputs

New deterministic artifacts should be consumed as `.json` files:

```text
atlas/source/snapshot.json
atlas/source/file-hashes.json
atlas/index/file-index.json
atlas/index/symbol-index.json
atlas/index/import-index.json
atlas/index/endpoint-index.json
atlas/index/route-index.json
atlas/index/api-client-index.json
atlas/index/schema-index.json
atlas/index/ui-action-index.json
atlas/index/test-index.json
atlas/runtime/dependency-map.json
atlas/runtime/middleware-map.json
atlas/runtime/router-inclusion-map.json
atlas/errors/python-exception-map.json
atlas/errors/frontend-error-map.json
atlas/payloads/opensearch-query-dsl.json
atlas/bindings/ecosystem-bindings-resolved.json
atlas/graph/nodes.json
atlas/graph/edges.json
atlas/graph/payload-graph.json
atlas/graph/error-flow-graph.json
atlas/flows/api-request-flows.json
atlas/flows/ui-action-flows.json
atlas/flows/error-flows.json
atlas/audit/v2-validation-report.json
atlas/audit/artifact-json-promotion-report.json
atlas/change/changed-files.json
atlas/visualizer/graph-data.json
atlas/visualizer/cytoscape-elements.json
```

Legacy `.yaml` JSON-compatible files may still exist for backward compatibility. New tools should prefer `.json` and only fall back to `.yaml` when needed.

## What the suite captures

### Snapshot

```text
repo id/role/path/framework/language
repo exists flag
file path/language/classification
file line count, size, and sha256 hash
missing repo/file read findings
```

### Python indexing

```text
functions/classes
line ranges
calls
imports
FastAPI-style route decorator candidates
Depends(...) candidates
APIRouter/FastAPI/include_router candidates
middleware candidates
exception/raise/try-except candidates
Pydantic/BaseModel schema candidates
OpenSearch search/msearch payload candidates where statically visible
test file candidates
```

### TypeScript/React indexing

```text
symbol candidates
React route candidates
API client call candidates
TanStack Query candidate packets
UI action candidates such as onClick/onSubmit
frontend error/catch candidates
library binding candidates for MUI, Leaflet, ReGraph, TanStack Query, React Router
```

### Graph/flow seeds

```text
node export
IMPLEMENTS edges
MAPS_TO edges where frontend API method/path matches backend endpoint method/path
BUILDS_QUERY edges for OpenSearch payload packets
RAISES_ERROR/HANDLES_ERROR edges for exception candidates
seed API request flows
seed UI action flows
seed error flows
```

### Drift/maintenance

```text
changed files
added files
removed files
```

Symbol-level drift is still a future hardening task.

## Important implementation note

The suite is plain Python source in:

```text
atlas/tools/codeatlas_v2_suite.py
atlas/tools/codeatlas_v2_canonical.py
```

Do not reintroduce encoded/base64 payload launchers. Kiro and humans must be able to read, modify, review, and test the tools directly.

## Current limitations

The V2 suite is still a foundation, not the full final framework.

Future bounded tasks should add:

```text
module refactor for maintainability
real TypeScript AST / ts-morph extraction
stronger Pydantic schema extractor
stronger FastAPI router-prefix/dependency/middleware materialisation
branch-aware API flow builder with condition paths
UI state/interaction flow builder
stronger OpenSearch/config extractor
fixture/mock/test archaeology extractor
contract checker
symbol-level impact-to-targeted-rerun planner
SQLite/DuckDB/Kuzu read models
visualizer UI
```
