# Codex Handoff: Atlas + ngk Trusted Engine Roadmap

Last updated: 2026-06-07

This is the implementation handoff for Codex. It captures the vision, reliability model, command framework, smart terminal integration, and phased roadmap for turning CodeAtlas output into a trusted developer engine.

The focus is not more generated prose. The focus is a reliable core that improves Kiro answer accuracy, review quality, debugging quality, and developer confidence by using Atlas-generated YAML/JSON/JSONL as evidence-backed source material.

---

## Vision

CodeAtlas should become the deterministic knowledge layer for a codebase.

```text
Application repos
  -> CodeAtlas extraction
  -> evidence-backed facts, graph, traces, contracts, source spans
  -> ngk indexing and retrieval
  -> Kiro context packs
  -> cited Kiro answers
  -> verification/audit
  -> smart terminal cockpit
```

The target workflow is:

```bash
ngk impact --changed
ngk test-select --changed
ngk review --changed
ngk verify-answer latest
ngk smart
```

The developer should trust the result because every meaningful claim resolves to stable Atlas fact IDs, source spans, extraction methods, confidence levels, and drift checks.

---

## Roles

### Atlas

Atlas is the source of truth. It generates deterministic artifacts:

```text
.atlas/
  manifest.json
  status.json
  facts/*.yaml
  graph/nodes.jsonl
  graph/edges.jsonl
  traces/flow_traces.jsonl
  indexes/source_spans.jsonl
  contracts/openapi.json
  contracts/pydantic_models.jsonl
  contracts/typescript_types.jsonl
  ui/*.jsonl
  api/*.jsonl
```

Atlas should not merely generate summaries. It should generate a machine-readable model of the repo.

### ngk

ngk is the command/control layer. It indexes Atlas, retrieves relevant knowledge, runs impact analysis, builds Kiro context packs, starts Kiro sessions, parses citations, audits answers, stores sessions, and feeds the smart terminal.

Runtime state belongs under `.ngk/`, not `.atlas/`:

```text
.ngk/
  cache/
    atlas.db
    citation_index.jsonl
    source_cards.jsonl
    retrieval_index.jsonl
    trace_cards.jsonl
  sessions/
    <session-id>/
      context-pack.md
      context-pack.json
      selected-facts.jsonl
      selected-traces.jsonl
      kiro-output.raw.md
      kiro-output.parsed.json
      citations.json
      audit.json
      events.jsonl
```

### Kiro

Kiro is the reasoning/agent layer. Kiro should not rediscover the codebase from scratch. ngk should give Kiro the smallest sufficient Atlas context pack.

Kiro must cite Atlas fact IDs for all architectural, API, UI, data-flow, business-rule, model, dependency, and test-coverage claims.

### Smart terminal

The smart terminal is the cockpit. It renders the current Kiro answer, citations, source previews, impact analysis, traces, drift status, related tests, and service status. It must not duplicate Atlas or ngk logic.

---

## Non-negotiable reliability rules

1. No fact without evidence.
2. No high-confidence fact without deterministic extraction.
3. No graph edge without source evidence or an explicit `needs_review: true` marker.
4. Every source span must include a file path, line range, commit or content hash, and extraction method.
5. If source code conflicts with Atlas artifacts, source code wins and Atlas is marked stale or contradicted.
6. Kiro must not cite Markdown summaries as primary evidence when structured facts exist.
7. Kiro output must be auditable.
8. Unsupported Kiro claims must be surfaced, not hidden.
9. UI impact analysis must use confidence tiers.
10. Review results must include affected facts/traces/tests, not only prose.
11. Strict mode must be able to fail local commands or CI if Atlas is stale or Kiro makes unsupported architectural claims.

Trusted means:

```text
claim -> fact_id -> Atlas YAML pointer -> source evidence -> extraction method -> drift status
```

---

## Canonical artifact contract

Codex should preserve compatibility with existing CodeAtlas V2 artifacts, but the trusted engine should normalize them into these concepts.

### Fact

```yaml
facts:
  - id: fact.api.property_search.endpoint
    claim: "The backend exposes GET /properties/search for property search."
    type: api_endpoint
    confidence: high
    subject:
      id: api.GET./properties/search
      kind: api_operation
      name: "GET /properties/search"
    atlas_pointer: ".atlas/facts/api_contracts.yaml#/facts/0"
    evidence:
      - evidence_id: evidence.api.property_search.route
        repo_id: repo.api
        path: api/app/routers/property.py
        lines: [22, 48]
        span_id: span.api.property_router.search_endpoint
        method: fastapi_route_extraction
      - evidence_id: evidence.api.property_search.openapi
        repo_id: repo.api
        path: api/openapi.json
        pointer: /paths/~1properties~1search/get
        method: openapi_generation
    verified_by:
      - fastapi_route_extraction
      - openapi_generation
    related:
      symbols:
        - symbol.api.search_properties
      traces:
        - trace.property_search.ui_to_opensearch
      tests:
        - test.api.test_property_search_success
```

### Source span

```json
{
  "span_id": "span.api.property_router.search_endpoint",
  "repo_id": "repo.api",
  "file_id": "file.api.app.routers.property.py",
  "path": "api/app/routers/property.py",
  "language": "python",
  "start_line": 22,
  "end_line": 48,
  "content_hash": "sha256:...",
  "commit": "...",
  "extracted_by": ["python_ast", "fastapi_route_extractor"]
}
```

### Graph edge

```json
{
  "edge_id": "edge.ui.query_hook.calls_api_client.property_search",
  "from": "symbol.ui.usePropertySearchQuery",
  "to": "symbol.ui.propertyApi.search",
  "type": "calls",
  "confidence": "high",
  "evidence": [
    {
      "span_id": "span.ui.usePropertySearchQuery",
      "path": "ui/src/features/property/usePropertySearchQuery.ts",
      "lines": [12, 51],
      "method": "typescript_ast"
    }
  ],
  "fact_ids": ["fact.ui.property_search.query_hook"]
}
```

### Flow trace

```json
{
  "trace_id": "trace.property_search.ui_to_opensearch",
  "title": "Property search UI to OpenSearch",
  "confidence": "high",
  "nodes": [
    {"node_id": "symbol.ui.SearchPage", "label": "SearchPage.tsx", "kind": "react_component", "step": 1},
    {"node_id": "symbol.ui.usePropertySearchQuery", "label": "usePropertySearchQuery", "kind": "react_hook", "step": 2},
    {"node_id": "api.GET./properties/search", "label": "GET /properties/search", "kind": "api_operation", "step": 3},
    {"node_id": "symbol.api.search_properties", "label": "search_properties()", "kind": "fastapi_endpoint", "step": 4},
    {"node_id": "data.opensearch.property_listings", "label": "property_listings", "kind": "opensearch_index", "step": 5}
  ],
  "related_tests": ["test.api.test_property_search_success"]
}
```

---

## Command groups to implement

```text
ngk atlas status/index/validate/doctor/watch
ngk drift
ngk sources <query>
ngk fact show/yaml/code/related <fact_id>
ngk trace <target>
ngk graph neighbors/path <target>
ngk impact <target|--changed>
ngk test-select <target|--changed>
ngk test-plan <target|--changed>
ngk ctx build/show/explain
ngk ask <question>
ngk verify-answer <session|latest>
ngk audit <session|latest>
ngk review <link|--changed>
ngk contract check
ngk eval run
ngk smart
ngk session list/show/replay
```

Global flags:

```text
--atlas .atlas
--ngk-dir .ngk
--config .ngk/config.yaml
--json
--strict
--verbose
--open-smart
--session <id>
```

---

## Implementation roadmap

### Phase 0: Repo integration and handoff alignment

Make this document discoverable, keep existing V2 canonical docs, and treat existing scripts as the baseline.

Acceptance criteria:

- New contributors can find this file from `docs/START_HERE_FOR_KIRO.md`.
- Existing V2 canonical commands continue to work.

### Phase 1: Schema contract and validators

Implement:

```bash
ngk atlas validate
ngk atlas doctor
```

Validation rules:

- Every fact has `id`, `claim`, `type`, `confidence`, and `evidence`.
- Every evidence item has a path plus line range, pointer, symbol ID, or explicit reason why source evidence is unavailable.
- Every high-confidence fact has deterministic `verified_by` methods.
- Every graph edge references known nodes.
- Every trace references known graph nodes or carries `needs_review: true`.
- Every low-confidence or inferred artifact is clearly marked.

Acceptance criteria: `ngk atlas validate --strict` fails on broken IDs, missing evidence, broken pointers, or unsupported high-confidence claims.

### Phase 2: Citation index and source span index

Implement:

```bash
ngk atlas index
ngk sources <query>
ngk fact show <fact_id>
ngk fact yaml <fact_id>
ngk fact code <fact_id>
```

Build cache:

```text
.ngk/cache/atlas.db
.ngk/cache/citation_index.jsonl
.ngk/cache/source_cards.jsonl
.ngk/cache/source_spans.jsonl
.ngk/cache/retrieval_index.jsonl
.ngk/cache/trace_cards.jsonl
```

Acceptance criteria:

- Given a fact ID, ngk can show claim, confidence, Atlas YAML pointer, original source path/lines, extraction method, related tests, and related traces.
- Source spans include content hashes.
- Missing spans are visible as validation warnings.

### Phase 3: Drift detection

Implement:

```bash
ngk drift
ngk drift --changed
ngk atlas status --strict
```

Detect:

- Indexed commit differs from current commit.
- Dirty files affect indexed facts.
- Source span hash mismatch.
- FastAPI routes are newer than OpenAPI artifacts.
- Pydantic model files are newer than OpenAPI/generated TS clients.
- Facts point to missing files or stale line ranges.
- Traces reference missing nodes.

Acceptance criteria:

- `ngk ask`, `ngk review`, and `ngk impact` warn when Atlas is stale.
- `--strict` fails when stale facts would be used.

### Phase 4: Deterministic graph engine

Implement:

```bash
ngk trace <target>
ngk graph neighbors <target>
ngk graph path <from> <to>
```

Core edge types:

```text
contains imports exports calls uses renders defines_route routes_to_component
uses_hook uses_query_key calls_api_client http_calls implements_api_operation
validates_with_model responds_with_model calls_service calls_repository
queries_opensearch_index reads_env_var covered_by_test
```

Acceptance criteria:

- `ngk trace PropertySearchRequest` shows upstream/downstream relationships with evidence.
- `ngk graph path symbol.ui.SearchPage api.GET./properties/search` works when graph data exists.

### Phase 5: UI Impact Analyzer MVP

UI impact is not as deterministic as API impact. Use confidence tiers.

High-confidence UI impact can come from:

```text
TypeScript imports/exports
symbol references
React component definitions
route-to-component mappings
component uses hook
hook calls API client
TanStack Query hook/query key usage
tests importing/rendering components
```

Medium-confidence UI impact can come from:

```text
form field names matching request model fields
prop names matching child component props
API payload object construction
feature directory conventions
```

Low-confidence UI impact can come from:

```text
spread props
runtime feature flags
dynamic imports
callback chains
string-built routes
visual/layout-only changes
```

Implement:

```bash
ngk impact ui/src/features/property/SearchPage.tsx
ngk impact symbol.ui.SearchPage
ngk impact --changed --ui
```

Acceptance criteria:

- No UI impact is described as definite unless backed by deterministic evidence.
- Dynamic/heuristic impact is clearly marked.
- UI impact can trace route -> component -> hook -> API client -> endpoint where evidence exists.

### Phase 6: API Impact Analyzer

Support targets:

```text
FastAPI route
OpenAPI operation
Pydantic model
Pydantic field
service function
repository/query function
OpenSearch index
OpenSearch field
```

Implement:

```bash
ngk impact PropertySearchRequest
ngk impact field.api.PropertySearchRequest.suburb
ngk impact "GET /properties/search"
ngk impact --changed --api
```

Acceptance criteria:

- Pydantic field impact can find endpoints, services, UI clients, query hooks, tests, and traces when graph data exists.
- API impact paths show confidence and evidence.
- Cross-stack impact is available when UI/API edges exist.

### Phase 7: Test selection and test planning

Implement:

```bash
ngk test-select --changed
ngk test-plan --changed
ngk test-select PropertySearchRequest
```

Output:

```text
High-confidence tests
Medium-confidence tests
Coverage gaps
Why each test was selected
Commands to run
```

Acceptance criteria:

- Each selected test has an explanation based on facts, graph edges, imports, coverage, or naming heuristics.
- Missing tests are surfaced as gaps.

### Phase 8: Kiro context engine

Implement:

```bash
ngk ctx build ask "How does property search work?"
ngk ctx build review --changed
ngk ctx explain latest
ngk ask "How does property search work?"
```

Context pack contents:

```text
mode
user request
Atlas freshness/drift status
retrieved facts
impact analysis
relevant traces
source evidence
related tests
citation rules
required output contract
```

Required Kiro output block:

```text
<atlas_citations>
{
  "claims": [
    {
      "claim_id": "claim.1",
      "text": "...",
      "support": "supported",
      "fact_ids": ["fact.example"]
    }
  ],
  "citations": [
    {
      "fact_id": "fact.example",
      "used_for_claims": ["claim.1"]
    }
  ],
  "not_confirmed": []
}
</atlas_citations>
```

Acceptance criteria:

- `ngk ctx explain latest` shows why facts/traces/sources were selected.
- Context packs prefer high-confidence facts and compact evidence.
- Kiro is told to say `Not confirmed by Atlas` for unsupported claims.

### Phase 9: ngk verify-answer / answer audit

Implement:

```bash
ngk verify-answer latest
ngk audit latest
ngk audit latest --strict
```

Checks:

- Cited fact IDs exist.
- Cited facts have evidence.
- Cited facts are fresh.
- Claims are supported by the cited facts.
- Low-confidence facts are not presented as certain.
- Unsupported claims are marked.
- Vague citations to summary docs are flagged when structured facts exist.

Acceptance criteria:

- Unsupported architectural/API/UI/data/test claims are visible.
- `--strict` fails on unsupported claims.
- Audit artifacts are written to `.ngk/sessions/<id>/audit.json`.

### Phase 10: Golden eval suite

Implement:

```bash
ngk eval init
ngk eval run
ngk eval add "How does property search work?"
```

Eval case shape:

```yaml
id: eval.property_search.flow
question: "How does property search work?"
must_retrieve:
  - fact.ui.property_search.query_hook
  - fact.api.property_search.endpoint
must_cite:
  - fact.api.property_search.endpoint
must_not_claim:
  - "GraphQL"
  - "Redis cache"
expected_trace:
  - trace.property_search.ui_to_opensearch
```

Acceptance criteria:

- Evals can run without mutating source code.
- Retrieval changes and prompt changes can be tested before release.

### Phase 11: Atlas-native review engine

Implement:

```bash
ngk review --changed
ngk review <github-pr-link>
ngk review --changed --strict
```

Review context should include diff, changed files, changed source spans, affected facts, affected traces, contract risk, test plan, drift status, Kiro review instructions, and citation requirements.

Review output should include finding, severity, affected fact IDs, affected traces, source evidence, suggested fix, suggested tests, confidence, and audit status.

Acceptance criteria:

- Review findings about architecture, APIs, UI flows, data flows, or test coverage cite Atlas facts.
- Review session is stored under `.ngk/sessions/`.
- `ngk verify-answer latest --strict` can validate the review.

### Phase 12: Contract checks

Implement:

```bash
ngk contract check
ngk contract check --changed
ngk contract api-ui
ngk contract data
```

Check:

- UI API client calls match OpenAPI operations.
- Pydantic request/response models match OpenAPI.
- UI form fields map to request model fields.
- UI response field usage exists in API response schema.
- OpenSearch fields used in query builders exist in known mappings.
- Generated clients are fresh relative to OpenAPI.

Acceptance criteria:

- Public contract changes are visible.
- Contract findings include source evidence and related tests.

### Phase 13: Smart terminal integration

Implement:

```bash
ngk smart
ngk smart --session latest
ngk smart ask "How does property search work?"
```

Panels:

```text
Kiro answer
Audit status
Sources used
Source preview
Code evidence
Impact graph
Affected tests
Drift warnings
Contract warnings
Session history
Service status
```

Acceptance criteria:

- The TUI reads ngk session/cache artifacts.
- The TUI does not duplicate retrieval, impact, or audit logic.
- It works cleanly in Kitty.

---

## UI Impact Analyzer detail

UI impact can be effective if implemented with confidence tiers and TypeScript-aware extraction.

Strong UI signals:

```text
import graph
export graph
TypeScript symbol references
route definitions
component render tree
custom hook usage
TanStack Query keys
API client function calls
generated client operation usage
test imports/render calls
```

Weaker UI signals:

```text
form field name similarity
object literal payloads
prop drilling
feature directory grouping
callback chains
CSS/layout coupling
```

Example output:

```text
Impact: SearchFilters.tsx

High-confidence impact:
  - SearchPage renders SearchFilters.
  - SearchPage uses usePropertySearchQuery.
  - usePropertySearchQuery calls propertyApi.search.

Medium-confidence impact:
  - SearchFilters appears to construct fields used by PropertySearchRequest.

Low-confidence impact:
  - Map marker rendering may be affected through callback props.

Related tests:
  - SearchPage.filters.test.tsx
  - usePropertySearchQuery.test.ts

Unknowns:
  - Spread props prevent exact field-level mapping in SearchFilters.
```

---

## ngk map guidance

Atlas already captures the map data through graph nodes, edges, facts, and traces.

Do not build `ngk map` as a separate source of truth.

Correct model:

```text
Atlas captures the map.
ngk trace/impact/review/smart render focused slices of the map.
ngk map, if implemented, is only a viewer/exporter.
```

Deprioritize `ngk map` until the trusted engine is solid.

---

## Suggested internal architecture

Implement ngk as services, not command-handler spaghetti.

```text
ngk/
  cli/
    main.py
    commands/
  core/
    config.py
    workspace.py
    ids.py
    errors.py
  atlas/
    loader.py
    indexer.py
    validator.py
    drift.py
  knowledge/
    facts.py
    citations.py
    sources.py
    spans.py
    graph.py
    traces.py
    retrieval.py
  impact/
    engine.py
    ui.py
    api.py
    tests.py
  context/
    builder.py
    templates/
      ask.md
      review.md
      debug.md
      plan.md
  agents/
    base.py
    kiro.py
    mock.py
  sessions/
    store.py
    parser.py
    audit.py
  review/
    changed.py
    github.py
    reviewer.py
  contract/
    checker.py
  evals/
    runner.py
  smart/
    app.py
    view_models.py
```

Core interfaces:

```text
AtlasStore
CitationIndex
SourceSpanIndex
GraphStore
TraceStore
RetrievalEngine
ImpactEngine
TestSelector
ContextPackBuilder
AgentRunner
AnswerAuditor
SessionStore
SmartTerminal
```

---

## Definition of done for the trusted core

The trusted core is good enough to rely on when these are true:

```text
1. Every displayed claim has a fact ID.
2. Every fact ID resolves to source evidence.
3. Every source span has a content hash.
4. Drift is detected before Kiro is invoked.
5. UI impact uses confidence tiers.
6. API impact is deterministic.
7. Kiro receives curated context, not repo dumps.
8. Kiro output is parsed and audited.
9. Unsupported Kiro claims are visible.
10. Golden evals protect against regressions.
11. Review output cites affected facts/traces.
12. Strict mode can fail CI or local review.
```

Until those are true, Atlas is useful but must not be treated as fully authoritative.
