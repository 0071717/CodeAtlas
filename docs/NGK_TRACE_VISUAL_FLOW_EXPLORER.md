# ngk trace Visual Flow Explorer

`ngk trace` is a downstream CodeAtlas tool that converts Atlas knowledge into a ReGraph-compatible visual payload.

## Goal

A developer can run:

```bash
ngk trace "POST /claims"
```

and receive a graph payload showing the full request lifecycle:

```text
React UI action
→ API client
→ FastAPI router
→ schema/dependency/middleware
→ service layer
→ data-access function
→ OpenSearch Query DSL
→ response/error UI state
```

## Inputs

The transformer should read, in priority order:

```text
atlas/knowledge/manifest.yaml
atlas/knowledge/nodes/*.yaml
atlas/knowledge/edges.yaml
atlas/knowledge/indexes/*.yaml
atlas/graph/nodes.yaml
atlas/graph/edges.yaml
atlas/flows/api-request-flows.yaml
atlas/flows/ui-action-flows.yaml
atlas/flows/error-flows.yaml
atlas/payloads/opensearch-query-dsl.yaml
atlas/testing/test-inventory.yaml
atlas/testing/coverage-gaps.yaml
atlas/bindings/ecosystem-bindings-resolved.yaml
```

The file-based Atlas artifacts remain canonical. A future SQLite, DuckDB, or Kuzu read model may be used for speed, but it must be compiled from the canonical files.

## Output

The exporter should write:

```text
atlas/visualizer/ngk-trace/<trace-id>.regraph.json
atlas/visualizer/ngk-trace/<trace-id>.summary.md
```

The initial JSON shape is intentionally adapter-friendly:

```json
{
  "items": {
    "node_id": {
      "label": "POST /claims",
      "type": "endpoint",
      "color": "#...",
      "data": { "atlas_id": "endpoint.claims.create" }
    }
  },
  "links": {
    "edge_id": {
      "id1": "source_node_id",
      "id2": "target_node_id",
      "label": "CALLS",
      "data": { "atlas_edge_id": "edge..." }
    }
  },
  "metadata": {
    "query": "POST /claims",
    "generated_at": "...",
    "confidence": "medium"
  }
}
```

If the consuming ReGraph component expects a different property shape, add a tiny adapter layer rather than changing Atlas internals.

## Node coloring

Suggested defaults:

```text
green: covered by tests
amber: partially covered / weak tests / needs review
red: untested high-value flow or unsupported claim
blue: external/data/search system
purple: UI node
orange: error path
gray: unknown or low-confidence
```

## OpenSearch node details

OpenSearch nodes should include:

```text
index or alias
operation
query DSL, if reconstructed
query builder source function
unresolved dynamic fields
confidence
source evidence
```

Clicking an OpenSearch node should show the exact DSL when available, or the partial DSL plus unresolved variables when not fully static.

## Implementation stages

### Stage 1 — file-based exporter

Build `atlas/tools/ngk_trace_regraph_exporter.py` that reads YAML/JSON artifacts and produces ReGraph JSON.

### Stage 2 — payload linking

Add Layer 1.5 outputs so OpenSearch DSL nodes can show query bodies.

### Stage 3 — error branching

Add Layer 5.5 outputs so error branches render as explicit graph branches.

### Stage 4 — fast local read model

Compile `atlas/knowledge` into SQLite/DuckDB/Kuzu for fast `ngk trace`, `ngk ask`, and `ngk review` queries.

## Kiro rule

If a trace cannot be fully resolved, do not invent missing links. Produce a graph with low-confidence placeholder nodes and a clear `missing_links` list.
