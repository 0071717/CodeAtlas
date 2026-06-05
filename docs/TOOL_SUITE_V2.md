# CodeAtlas V2 Deterministic Tool Suite

This guide describes the deterministic tools added for CodeAtlas V2.

The suite is intentionally readable, dependency-light, and fast. It creates the foundation Kiro can inspect and improve without repeatedly asking an AI to rescan the whole project.

## Current foundation outputs

```text
atlas/source/snapshot.yaml
atlas/source/file-hashes.yaml
atlas/index/file-index.yaml
atlas/index/symbol-index.yaml
atlas/index/import-index.yaml
atlas/index/endpoint-index.yaml
atlas/index/route-index.yaml
atlas/index/component-index.yaml
atlas/index/hook-index.yaml
atlas/index/api-client-index.yaml
atlas/index/schema-index.yaml
atlas/index/service-index.yaml
atlas/index/data-access-index.yaml
atlas/index/runtime-entrypoint-index.yaml
atlas/index/ui-action-index.yaml
atlas/index/test-index.yaml
atlas/index/config-index.yaml
atlas/runtime/runtime-map.yaml
atlas/testing/test-inventory.yaml
atlas/graph/nodes.yaml
atlas/graph/edges.yaml
atlas/flows/api-request-flows.yaml
atlas/flows/ui-flows.yaml
atlas/audit/v2-validation-report.yaml
atlas/change/changed-files.yaml
atlas/change/impacted-nodes.yaml
atlas/change/impacted-edges.yaml
atlas/change/targeted-rerun-plan.yaml
atlas/visualizer/graph-data.json
atlas/visualizer/cytoscape-elements.json
atlas/visualizer/node-detail-index.json
atlas/visualizer/flow-cards.json
```

## Commands

Run all foundation steps:

```bash
python3 atlas/tools/codeatlas_v2_suite.py all
```

Or run individual steps:

```bash
python3 atlas/tools/codeatlas_v2_suite.py init
python3 atlas/tools/codeatlas_v2_suite.py snapshot
python3 atlas/tools/codeatlas_v2_suite.py index
python3 atlas/tools/codeatlas_v2_suite.py graph
python3 atlas/tools/codeatlas_v2_suite.py validate
python3 atlas/tools/codeatlas_v2_suite.py drift-check
python3 atlas/tools/codeatlas_v2_suite.py visualizer-export
```

Runner:

```bash
bash atlas/scripts/run-framework-v2-suite.sh
```

## What the suite now captures

### Snapshot

```text
repo id/role/path/framework/language
repo exists flag
git branch and commit when available
file path/language/classification/analysis depth
file line count, size, and sha256 hash
missing repo/file read findings
```

### Python indexing

```text
functions/classes
signatures, signature hashes, body hashes
line ranges
calls
imports
branch summaries from if-statements
raise summaries
FastAPI-style route decorator candidates
Pydantic/BaseModel schema candidates
service/data-access candidates
middleware/dependency/exception handler candidates
pytest/test function candidates
```

### TypeScript/React indexing

```text
symbol candidates
component candidates
hook candidates
React route candidates
API client call candidates
UI action candidates such as onClick/onSubmit/onChange
test file/function candidates
imports
```

### Graph/flow seeds

```text
node export
IMPLEMENTS edges
CALLS edges where symbol names match
MAPS_TO edges where frontend API method/path matches backend endpoint method/path
seed API request flows with runtime envelope, branches, and error exits
seed UI flows with route/action/API-call states where available
```

### Drift/maintenance

```text
changed files
added files
removed files
impacted nodes
impacted edges
targeted rerun recommendation
```

### Visualization

```text
graph-data.json
cytoscape-elements.json
node-detail-index.json
flow-cards.json
```

## Important implementation note

The suite is plain Python source in:

```text
atlas/tools/codeatlas_v2_suite.py
```

Do not reintroduce encoded/base64 payload launchers. Kiro and humans must be able to read, modify, review, and test the tool directly.

## Current limitations

The V2 suite is still a foundation, not the full final framework. It uses Python standard library plus optional PyYAML if available.

Future bounded tasks should add:

```text
module refactor for maintainability
stronger TypeScript/React parser
stronger Pydantic schema extractor
stronger FastAPI router-prefix/dependency/middleware extractor
branch-aware API flow builder with condition paths
UI state/interaction flow builder
OpenSearch/config extractor
fixture/mock/test archaeology extractor
contract checker
impact-to-targeted-rerun planner
visualizer UI
```

## Output format

The files use JSON syntax with `.yaml` extensions for now. JSON is valid YAML and easier to parse with Python standard library. A later task may switch to a YAML library if desired, but deterministic parsability matters more than formatting.
