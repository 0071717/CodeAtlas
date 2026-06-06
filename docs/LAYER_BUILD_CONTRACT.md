# CodeAtlas Layer Build Contract

Every CodeAtlas V2 layer must be implemented as a bounded, testable build step.

A layer is not a prompt. A layer is a contract with inputs, outputs, schemas, validation, confidence handling, and rerun rules.

## Required layer fields

Each layer definition must document:

```text
name
purpose
inputs
outputs
builder
validator
schema
confidence policy
source fallback policy
rerun policy
known limitations
acceptance criteria
```

## Standard layer shape

```yaml
layer:
  id: graph.relationships
  name: Relationship graph
  purpose: Connect indexed and mapped entities with typed relationships.
  inputs:
    - atlas/index/*.yaml
    - atlas/map/*.yaml
  outputs:
    - atlas/graph/nodes.yaml
    - atlas/graph/edges.yaml
  builder:
    deterministic_first: true
    script: atlas/tools/codeatlas_v2_suite.py graph
    ai_enrichment_allowed: bounded_only
  validator:
    - schema validation
    - source/target link validation
    - evidence validation
  confidence_policy:
    high: direct deterministic evidence
    medium: structural inference with supporting evidence
    low: plausible but incomplete/runtime-dependent
  source_fallback_policy: only inspect raw source when lower-layer evidence is missing or stale
  rerun_policy: rerun when impacted index/map nodes change
```

## Fractional layer contracts

Fractional layers exist when the normal pipeline has an information gap that would otherwise force AI to guess.

### Layer 1.5 — Data payload and DSL reconstruction

Purpose: reconstruct request/response/search/query payloads before semantic inference.

Required outputs:

```text
atlas/payloads/request-payloads.yaml
atlas/payloads/response-payloads.yaml
atlas/payloads/opensearch-query-dsl.yaml
atlas/payloads/sql-queries.yaml
atlas/payloads/generated-query-builders.yaml
atlas/graph/payload-graph.yaml
```

Acceptance criteria:

```text
query builder functions are linked to data-access calls
static query fragments are captured
dynamic fragments are marked unresolved rather than invented
OpenSearch nodes expose exact or partial Query DSL where possible
```

### Layer 3.5 — Ecosystem and third-party bindings

Purpose: map imported libraries/framework components to semantic roles used by downstream tools.

Required inputs and outputs:

```text
input:  atlas/config/ecosystem-bindings.yaml
input:  atlas/index/import-index.yaml
input:  atlas/index/component-index.yaml
output: atlas/bindings/ecosystem-bindings-resolved.yaml
output: atlas/map/library-semantics-map.yaml
output: atlas/graph/ecosystem-binding-graph.yaml
```

Acceptance criteria:

```text
Leaflet/react-leaflet components can become geospatial UI nodes
ReGraph components can become graph visualization UI nodes
TanStack Query hooks can become server-state/query/mutation nodes
OpenSearch clients can become search/data-access nodes
unknown imports are emitted as findings, not ignored
```

### Layer 5.5 — Explicit error and exception flows

Purpose: map failure paths before full conditional flow generation.

Required outputs:

```text
atlas/errors/python-exception-map.yaml
atlas/errors/frontend-error-map.yaml
atlas/errors/error-boundary-map.yaml
atlas/errors/opensearch-error-map.yaml
atlas/flows/error-flows.yaml
atlas/graph/error-flow-graph.yaml
```

Acceptance criteria:

```text
Python raise sites and try/except handlers are indexed
FastAPI HTTPException status codes are captured where static
frontend catch blocks, ErrorBoundaries, and TanStack error states are indexed
error branches can be rendered by downstream visualizers
```

## Source fallback rule

Higher layers should not freely rescan the entire application.

Allowed source fallback cases:

```text
missing evidence
stale file or symbol hash
low-confidence claim that blocks downstream tool output
verification challenge requires direct code check
user explicitly asks for implementation work
```

## Output rules

All output items should include where applicable:

```text
id
type or kind
repo
file/domain
confidence
needs_review
evidence
generated_at or source_artifact
```

## Evidence rules

Evidence should point to the lowest reliable support:

```yaml
evidence:
  - type: code
    repo: backend
    file: app/routers/claims.py
    symbol: create_claim
    line_start: 42
    line_end: 88
```

If no evidence exists, do not omit the uncertainty. Use:

```yaml
confidence: low
needs_review: true
verification_status: insufficient_evidence
```

## Deterministic-first rule

Use deterministic extraction for:

```text
file lists
hashes
line counts
symbols
imports
routes/endpoints
schemas
basic calls
payload/DSL reconstruction where static
ecosystem binding resolution
raise/except/catch/ErrorBoundary discovery
test files
YAML/JSON parse checks
link checks
changed-file detection
```

Use AI only after deterministic extraction has created bounded inputs.

## Layer acceptance checklist

A layer is acceptable when:

```text
outputs are written to the documented paths
outputs parse successfully
stable IDs are present
confidence and needs_review are used consistently
evidence is present for high-confidence claims
validation artifacts exist under atlas/audit/ or atlas/change/
limitations are documented
```
