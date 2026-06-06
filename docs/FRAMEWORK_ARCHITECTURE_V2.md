# CodeAtlas Framework Architecture V2

This document defines the next CodeAtlas architecture for deterministic, fast, evidence-backed reverse engineering of mature codebases.

The earlier framework established the vision: architecture-first, map-first, knowledge-layer-first. V2 makes the implementation more explicit by separating source evidence, indexes, maps, graphs, flows, facts, rules, requirements, tools, and verification.

## Core thesis

CodeAtlas should behave like a compiler for project knowledge:

```text
source repos
→ source/provenance snapshot
→ deterministic indexes
→ payload/DSL reconstruction
→ semantic maps
→ ecosystem bindings
→ runtime context
→ relationship graphs
→ explicit error flows
→ conditional flows
→ evidence-backed facts
→ rules and requirements
→ tool-specific context packs
→ verification and drift management
```

Kiro should not repeatedly reread the entire application with different prompts. Kiro should build and run deterministic tools first, then use AI only for bounded semantic enrichment, ambiguity resolution, summaries, rule derivation, and tool planning.

## The V2 planes

### 0. Scope and source provenance plane

Purpose: know exactly what was analysed.

Outputs:

```text
atlas/source/snapshot.yaml
atlas/source/file-hashes.yaml
atlas/source/extraction-scope.yaml
atlas/source/repo-manifest.yaml
```

Capture for every in-scope file:

```text
repo id
repo role
path
language
line count
size
sha256 hash
git blob sha where available
classification
analysis depth
indexed commit
```

Every higher-level claim should trace back to this plane.

### 1. Structural index plane

Purpose: know what exists, without yet interpreting business meaning.

Outputs:

```text
atlas/index/file-index.yaml
atlas/index/symbol-index.yaml
atlas/index/import-index.yaml
atlas/index/route-index.yaml
atlas/index/component-index.yaml
atlas/index/hook-index.yaml
atlas/index/api-client-index.yaml
atlas/index/endpoint-index.yaml
atlas/index/schema-index.yaml
atlas/index/service-index.yaml
atlas/index/data-access-index.yaml
atlas/index/test-index.yaml
atlas/index/config-index.yaml
```

This layer should be deterministic-first: Python AST, TypeScript compiler APIs or tree-sitter, grep, Git metadata, and config parsers.

### 1.5. Data payload and DSL reconstruction plane

Purpose: reconstruct important payloads that plain call graphs cannot explain.

Why this exists: AST structure can show `os_client.search(body=query)`, but a developer needs the shape of `query`, its filters, indexes, and dynamic inputs before AI can safely infer technical facts or business rules.

Outputs:

```text
atlas/payloads/request-payloads.yaml
atlas/payloads/response-payloads.yaml
atlas/payloads/opensearch-query-dsl.yaml
atlas/payloads/sql-queries.yaml
atlas/payloads/generated-query-builders.yaml
atlas/graph/payload-graph.yaml
```

Capture:

```text
OpenSearch index names and aliases
query builder functions
static JSON/query fragments
dynamic query variables
filter/range/match/terms clauses
sort/aggregation clauses
request and response shapes
payload source evidence
unresolved dynamic fields
```

Confidence rule: fully static payloads can be high confidence; composed payloads with unresolved variables are medium; runtime-only payloads are low and must include `needs_review: true`.

### 2. Runtime entrypoint plane

Purpose: find where execution or user interaction starts.

Entrypoints include:

```text
FastAPI endpoints
FastAPI middleware
FastAPI dependencies
exception handlers
startup/shutdown handlers
background jobs
React routes
forms
actions/buttons
API clients
sample-data generation commands
webhooks
CLI commands
```

Outputs:

```text
atlas/index/endpoint-index.yaml
atlas/index/runtime-entrypoint-index.yaml
atlas/index/ui-action-index.yaml
atlas/index/background-job-index.yaml
```

### 3. Semantic architecture plane

Purpose: classify indexed things by application role.

Outputs:

```text
atlas/architecture/domains.yaml
atlas/architecture/frontend-architecture.yaml
atlas/architecture/backend-architecture.yaml
atlas/architecture/data-architecture.yaml
atlas/architecture/integration-architecture.yaml

atlas/map/frontend-map.yaml
atlas/map/backend-map.yaml
atlas/map/component-map.yaml
atlas/map/form-map.yaml
atlas/map/api-map.yaml
atlas/map/schema-map.yaml
atlas/map/service-map.yaml
atlas/map/data-access-map.yaml
atlas/map/validation-map.yaml
atlas/map/permission-map.yaml
atlas/map/error-map.yaml
atlas/map/state-map.yaml
```

Backend traversal:

```text
router endpoint
→ middleware/dependencies
→ request schema
→ permission/auth checks
→ service
→ helper/service calls
→ data access/search/external system
→ response schema
→ errors/side effects
```

Frontend traversal:

```text
route
→ page/layout
→ component/form
→ hook/state/query/mutation
→ API client
→ backend endpoint
→ loading/error/success/empty UI states
```

### 3.5. Ecosystem and third-party bindings plane

Purpose: give deterministic semantic meaning to framework/library nodes that ASTs see only as imports or component calls.

Why this exists: components like `MapContainer` or `Graph` are not generic UI widgets in your ecosystem. They should become typed semantic nodes such as geospatial UI, graph visualization UI, map marker layer, graph node-link visualization, or atlas visualizer surface.

Inputs:

```text
atlas/config/ecosystem-bindings.yaml
atlas/index/import-index.yaml
atlas/index/component-index.yaml
atlas/index/react-router-index.yaml
atlas/index/tanstack-query-index.yaml
atlas/index/material-ui-index.yaml
```

Outputs:

```text
atlas/bindings/ecosystem-bindings-resolved.yaml
atlas/map/library-semantics-map.yaml
atlas/graph/ecosystem-binding-graph.yaml
```

Recommended binding categories:

```text
react_router_dom: routing/navigation
@tanstack/react-query: server-state/query/mutation/cache
leaflet/react-leaflet: geospatial UI/map layers/markers/popups
regraph: graph visualization/node-link analysis
@mui/material: UI component library/forms/dialogs/tables/alerts
opensearch client: search/query DSL/data access
ngk: developer CLI/orchestration surface
```

### 4. Cross-cutting runtime plane

Purpose: capture behaviour that wraps or modifies normal flows.

Outputs:

```text
atlas/runtime/middleware-map.yaml
atlas/runtime/dependency-map.yaml
atlas/runtime/exception-handler-map.yaml
atlas/runtime/logging-map.yaml
atlas/runtime/auth-map.yaml
atlas/runtime/config-map.yaml
atlas/runtime/feature-flag-map.yaml
```

FastAPI middleware, logging frameworks, request IDs, auth dependencies, global exception handlers, CORS, rate limiting, environment config, and feature flags belong here. They should be attached to flows as runtime envelopes rather than treated as ordinary service calls.

### 5. Relationship and contract graph plane

Purpose: connect mapped entities with typed relationships.

Outputs:

```text
atlas/graph/nodes.yaml
atlas/graph/edges.yaml
atlas/graph/call-graph.yaml
atlas/graph/dependency-graph.yaml
atlas/graph/ui-component-graph.yaml
atlas/graph/ui-to-api-graph.yaml
atlas/graph/contract-graph.yaml
atlas/graph/payload-graph.yaml
atlas/graph/test-coverage-graph.yaml
```

Recommended edge types:

```text
OWNS
CONTAINS
CALLS
MAPS_TO
VALIDATES
REQUIRES_PERMISSION
RETURNS
RAISES_ERROR
READS
WRITES
EMITS_EVENT
USES_CONFIG
USES_SCHEMA
USES_PAYLOAD
BUILDS_QUERY
HANDLES_ERROR
RENDERS_ERROR_STATE
TESTS
DERIVED_FROM
EVIDENCED_BY
IMPACTED_BY
```

### 5.5. Explicit error and exception flow plane

Purpose: map failure paths before building full conditional flows.

Why this exists: happy paths are easy; useful debugging requires deterministic knowledge of `try/except`, `raise`, `HTTPException`, global exception handlers, OpenSearch timeouts, frontend `.catch()`, TanStack `isError`, React ErrorBoundaries, and rendered error states.

Outputs:

```text
atlas/errors/python-exception-map.yaml
atlas/errors/frontend-error-map.yaml
atlas/errors/error-boundary-map.yaml
atlas/errors/opensearch-error-map.yaml
atlas/flows/error-flows.yaml
atlas/graph/error-flow-graph.yaml
```

Capture:

```text
raise sites
try/except handlers
HTTP status codes
OpenSearch exception handling
frontend catch blocks
TanStack error states
ErrorBoundary components
error alerts/snackbars/dialogs
fallback UI states
```

### 6. Conditional behaviour flow plane

Purpose: answer what happens in order.

Outputs:

```text
atlas/flows/api-request-flows.yaml
atlas/flows/ui-flows.yaml
atlas/flows/ui-action-flows.yaml
atlas/flows/data-flows.yaml
atlas/flows/error-flows.yaml
atlas/flows/permission-flows.yaml
atlas/flows/state-transition-flows.yaml
atlas/flows/sample-data-flows.yaml
```

API flows are conditional execution graphs: common path, branches, error exits, middleware envelope, side effects, external calls, OpenSearch DSL payloads, and unknown/dynamic dispatch.

UI flows are state machines: route, render state, user action, form state, validation state, loading state, API result, success/error/empty state, navigation, toast, cache effects, map state, and graph visualization state.

### 7. Fact plane

Purpose: create objective, evidence-backed statements from maps, graphs, flows, payloads, and error maps.

Output:

```text
atlas/facts/technical-facts.yaml
```

Facts should be boring and verifiable. Do not turn facts directly into business meaning without the rule layer.

### 8. Rule and requirement plane

Purpose: derive higher-level meaning from facts.

Outputs:

```text
atlas/rules/technical-rules.yaml
atlas/rules/business-rules.yaml
atlas/requirements/user-stories.yaml
atlas/requirements/acceptance-criteria.yaml
atlas/requirements/epics.yaml
atlas/requirements/high-level-requirements.yaml
```

Traceability ladder:

```text
code evidence
→ map node
→ payload/DSL node
→ graph edge
→ error-flow edge
→ flow step
→ technical fact
→ technical rule
→ business rule
→ user story
→ acceptance criterion
→ epic
→ high-level requirement
```

### 9. Testing and coverage plane

Purpose: understand existing tests and generate better tests.

Outputs:

```text
atlas/testing/test-inventory.yaml
atlas/testing/python-test-map.yaml
atlas/testing/fixture-map.yaml
atlas/testing/mock-map.yaml
atlas/testing/ui-test-candidates.yaml
atlas/testing/api-test-candidates.yaml
atlas/testing/e2e-test-candidates.yaml
atlas/testing/coverage-gaps.yaml
atlas/testing/playwright-plan.yaml
atlas/testing/api-test-plan.yaml
```

Existing poor tests are still useful. Map fixtures, mocks, weak assertions, historical edge cases, and missing coverage. Downstream visualizers should color nodes by coverage status where possible.

### 10. Knowledge normalization plane

Purpose: export a compact, queryable, agent-friendly source of truth.

Outputs:

```text
atlas/knowledge/manifest.yaml
atlas/knowledge/nodes/*.yaml
atlas/knowledge/edges.yaml
atlas/knowledge/indexes/*.yaml
atlas/knowledge/graph/*.json
atlas/knowledge/cards/*.json
atlas/knowledge/atlas.duckdb
atlas/knowledge/atlas.sqlite
atlas/knowledge/atlas.kuzu
```

The file-based YAML/JSON layer remains canonical and reviewable. Optional local databases are compiled read models for fast `ngk` queries, visualizers, and graph traversal.

### 11. Verification and challenge plane

Purpose: keep Atlas honest.

Outputs:

```text
atlas/audit/schema-validation.yaml
atlas/audit/link-validation.yaml
atlas/audit/source-verification.yaml
atlas/audit/flow-verification.yaml
atlas/audit/payload-verification.yaml
atlas/audit/error-flow-verification.yaml
atlas/audit/contract-mismatches.yaml
atlas/audit/adversarial-review.yaml
atlas/audit/unsupported-claims.yaml
atlas/audit/stale-nodes.yaml
atlas/audit/targeted-rerun-plan.yaml
```

Validators should include schema validation, ID/link validation, deterministic source checks, payload reconstruction checks, contract checks, error-flow checks, full-flow checks, and bounded adversarial AI review.

### 12. Consumption and tool plane

Purpose: produce useful developer-facing tools.

Tools should include:

```text
ngk trace visual flow exporter
debug navigator
feature impact planner
PR/MR impact analyzer
code health analyzer
contract checker
test gap analyzer
Playwright planner/generator
API test planner/generator
sample-data planner
refactor planner
release impact reporter
visualizer exporter
context pack generator
project Kiro agent builder
```

### 13. Change impact and targeted rerun plane

Purpose: keep Atlas fast and current.

Outputs:

```text
atlas/change/changed-files.yaml
atlas/change/changed-symbols.yaml
atlas/change/impacted-nodes.yaml
atlas/change/impacted-flows.yaml
atlas/change/impacted-rules.yaml
atlas/change/impacted-tests.yaml
atlas/change/targeted-rerun-plan.yaml
atlas/change/pr-impact-report.md
```

On every MR, use changed files and symbols to rerun only affected layers.

## Core implementation rule

Every layer must declare:

```text
inputs
outputs
schema
builder
validator
confidence policy
rerun policy
known limitations
```

## Kiro rule

Kiro should use deterministic tools for structure, graphs, drift, and validation. Kiro should use AI for bounded semantic enrichment, summaries, rule derivation, test scenario planning, UI/UX judgement, and adversarial challenge review.

If generated Atlas artifacts conflict with source code, source code wins and the Atlas artifact must be marked stale or unsupported.
