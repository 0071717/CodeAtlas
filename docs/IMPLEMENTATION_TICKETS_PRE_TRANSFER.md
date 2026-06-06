# Pre-Transfer Implementation Tickets

These are the remaining high-value tickets that should be executed by Kiro/Codex after the repo is transferred or in the final pre-transfer window. Each ticket is intentionally bounded.

## CA-V2-001 — Promote canonical V2 path everywhere

Objective: Ensure Kiro always starts with the deterministic V2 path.

Files:

```text
README.md
docs/START_HERE_FOR_KIRO.md
docs/CANONICAL_EXECUTION_PATH.md
docs/LEGACY_AND_EXPERIMENTAL_PATHS.md
atlas/scripts/run-framework-v2-suite.sh
```

Done when:

```text
No first-run guide recommends run-auto.sh as default.
V2 canonical wrapper is the documented first command.
Legacy scripts are documented as exploratory only.
```

## CA-V2-002 — Finish JSON artifact migration

Objective: Make `.json` canonical and `.yaml` fallback only.

Files:

```text
atlas/tools/codeatlas_v2_canonical.py
atlas/tools/codeatlas_v2_suite.py
atlas/tools/ngk_trace_regraph_exporter.py
docs/TOOL_SUITE_V2.md
```

Steps:

```text
1. Ensure V2 canonical runner writes/promotes JSON artifacts.
2. Update readers to prefer .json and fall back to .yaml.
3. Add validation warning for legacy .yaml files.
4. Keep backwards compatibility until all tools are migrated.
```

Validation:

```bash
python3 atlas/tools/codeatlas_v2_canonical.py all
python3 atlas/tools/codeatlas_v2_canonical.py validate
```

## CA-V2-003 — Build FastAPI materialisation extractor

Objective: Resolve FastAPI app/router/include_router/dependencies into materialised endpoint records.

Create:

```text
atlas/tools/backend/extract_fastapi_materialized.py
atlas/index/router-index.json
atlas/index/materialized-endpoint-index.json
atlas/runtime/dependency-map.json
atlas/runtime/router-inclusion-map.json
```

Acceptance:

```text
APIRouter prefixes are applied.
include_router chains are represented.
Depends(...) references are linked to symbols where possible.
Router-level and endpoint-level dependencies are distinguished.
```

## CA-V2-004 — Build TypeScript AST frontend extractor

Objective: Replace regex as canonical frontend extraction.

Create:

```text
atlas/tools/frontend/package.json
atlas/tools/frontend/src/extract-routes.ts
atlas/tools/frontend/src/extract-tanstack-query.ts
atlas/tools/frontend/src/extract-api-clients.ts
atlas/tools/frontend/src/extract-ui-actions.ts
atlas/tools/frontend/src/extract-leaflet-regraph.ts
```

Recommended parser:

```text
ts-morph first
tree-sitter optional for fast broad scanning
```

Acceptance:

```text
React Router route objects and JSX routes are captured.
TanStack query/mutation hooks include queryKey/mutationFn/queryFn where static.
Leaflet/ReGraph components are captured as semantic UI nodes.
API client calls are normalized.
```

## CA-V2-005 — Build OpenSearch Query DSL extractor

Objective: Implement Layer 1.5 payload/DSL reconstruction.

Create:

```text
atlas/tools/backend/extract_opensearch_payloads.py
atlas/payloads/opensearch-query-dsl.json
atlas/payloads/generated-query-builders.json
atlas/graph/payload-graph.json
```

Acceptance:

```text
Literal query dicts are captured.
search/msearch body=... calls are linked to owner symbols.
Dynamic unresolved variables are listed, not invented.
OpenSearch nodes can show Query DSL in ngk trace.
```

## CA-V2-006 — Build explicit error-flow extractor

Objective: Implement Layer 5.5 error/exception flows.

Create:

```text
atlas/tools/build_error_flows.py
atlas/errors/python-exception-map.json
atlas/errors/frontend-error-map.json
atlas/errors/error-boundary-map.json
atlas/flows/error-flows.json
atlas/graph/error-flow-graph.json
```

Acceptance:

```text
Python raise/try/except sites are represented.
HTTPException status codes are captured where static.
React catch/ErrorBoundary/TanStack error states are represented.
ngk trace can display error branches.
```

## CA-V2-007 — Build test archaeology mapper

Objective: Link existing tests to endpoints/routes/services/flows.

Create:

```text
atlas/tools/testing/map_test_coverage.py
atlas/testing/test-inventory.json
atlas/testing/fixture-map.json
atlas/testing/mock-map.json
atlas/testing/coverage-links.json
atlas/testing/coverage-gaps.json
```

Acceptance:

```text
FastAPI TestClient calls are linked to endpoint IDs.
pytest fixtures are mapped.
Mocks are classified.
Weak vs partial vs strong coverage is represented.
ngk trace can color nodes by coverage.
```

## CA-V2-008 — Build SQLite read model

Objective: Compile canonical file artifacts into a fast local read model for ngk.

Create:

```text
atlas/db/schema.sql
atlas/db/load_sqlite.py
atlas/knowledge/atlas.sqlite
```

Acceptance:

```text
nodes, edges, files, flows, payloads, errors, tests, evidence are queryable.
ngk can query SQLite before falling back to raw files.
YAML/JSON remains canonical; SQLite is derived.
```

## CA-V2-009 — Replace ngk trace BFS with trace bundles

Objective: Make ngk trace render deterministic trace bundles rather than free graph neighbourhoods.

Create:

```text
atlas/tools/build_trace_bundles.py
atlas/traces/trace-bundles.json
atlas/visualizer/ngk-trace/*.regraph.json
```

Acceptance:

```text
Trace starts from materialized endpoint or UI route ID.
Common path, branches, errors, payloads, and tests are explicit.
Missing links appear as findings, not invisible omissions.
```

## CA-V2-010 — Add prompt-safety and artifact redaction

Objective: Prevent secrets/PII/config leakage through prompts and generated knowledge.

Create:

```text
atlas/tools/security/redact_artifacts.py
atlas/audit/redaction-report.json
atlas/config/redaction-policy.yaml
```

Acceptance:

```text
.env and secret-like values are never sent to AI prompts.
Sensitive payloads can be hashed or redacted.
Artifacts are classified as prompt-safe or restricted.
```
