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
python3 atlas/tools/codeatlas_v2_canonical.py semantic-layers
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

The suite writes JSON-compatible legacy `.yaml` files first, then the canonical
wrapper promotes those files to `.json` equivalents for new consumers. Existing
Kiro prompts may still read `.yaml`; new tools should prefer `.json`.

Core outputs include:

```text
atlas/source/snapshot.{yaml,json}
atlas/source/file-hashes.{yaml,json}
atlas/index/file-index.{yaml,json}
atlas/index/symbol-index.{yaml,json}
atlas/index/import-index.{yaml,json}
atlas/index/endpoint-index.{yaml,json}
atlas/index/route-index.{yaml,json}
atlas/index/api-client-index.{yaml,json}
atlas/index/schema-index.{yaml,json}
atlas/index/service-index.{yaml,json}
atlas/index/data-access-index.{yaml,json}
atlas/index/runtime-entrypoint-index.{yaml,json}
atlas/index/ui-action-index.{yaml,json}
atlas/index/test-index.{yaml,json}
atlas/index/config-index.{yaml,json}
atlas/runtime/runtime-map.{yaml,json}
atlas/payloads/api-contracts.{yaml,json}
atlas/errors/error-flow-index.{yaml,json}
atlas/facts/technical-facts.{yaml,json}
atlas/graph/nodes.{yaml,json}
atlas/graph/edges.{yaml,json}
atlas/flows/api-request-flows.{yaml,json}
atlas/flows/ui-flows.{yaml,json}
atlas/knowledge/nodes/normalized-nodes.{yaml,json}
atlas/knowledge/graph/normalized-graph.{yaml,json}
atlas/knowledge/indexes/id-index.{yaml,json}
atlas/audit/v2-validation-report.{yaml,json}
atlas/audit/artifact-json-promotion-report.json
atlas/change/changed-files.{yaml,json}
atlas/change/impacted-nodes.{yaml,json}
atlas/change/impacted-edges.{yaml,json}
atlas/change/targeted-rerun-plan.{yaml,json}
atlas/visualizer/graph-data.json
atlas/visualizer/cytoscape-elements.json
atlas/visualizer/node-detail-index.json
atlas/visualizer/flow-cards.json
```

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

### Graph, flow, and semantic seeds

```text
node export
IMPLEMENTS edges
CALLS edges where symbol resolution is deterministic enough to review
MAPS_TO edges where frontend API method/path matches backend endpoint method/path
EVIDENCED_BY edges for schema/service/data-access/test/config records
seed API request flows
seed UI flows
request/response contract hints from Python signatures and Pydantic schema matches
explicit and unresolved endpoint error-flow records
evidence-backed technical fact seeds
normalized knowledge graph/read-model files for downstream tools
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
