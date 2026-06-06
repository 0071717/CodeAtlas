# ngk Ecosystem Hardening Plan

This plan adapts CodeAtlas V2 to an ecosystem with `ngk`, FastAPI, React/TypeScript, Leaflet, ReGraph, and OpenSearch.

## 1. TypeScript deterministic extraction

Regex extraction is a temporary foundation only. Replace or supplement it with a Node-based TypeScript AST tool.

Recommended path:

```text
atlas/tools/ts_ast_indexer/
  package.json
  src/index.ts
  src/extractReactRouter.ts
  src/extractTanStackQuery.ts
  src/extractLeaflet.ts
  src/extractReGraph.ts
  src/extractApiClients.ts
```

Preferred parser: `ts-morph` when type-aware project context is available. Use tree-sitter for very fast broad syntax scans or when project type-checking is too slow.

Outputs:

```text
atlas/index/import-index.yaml
atlas/index/component-index.yaml
atlas/index/react-router-index.yaml
atlas/index/tanstack-query-index.yaml
atlas/index/leaflet-index.yaml
atlas/index/regraph-index.yaml
atlas/index/api-client-index.yaml
atlas/index/ui-action-index.yaml
```

## 2. FastAPI deterministic dependency tracing

Improve Python analysis from name strings to module-aware symbol resolution.

Required index additions:

```text
module path → imported names
import alias → fully qualified source
router variable → APIRouter instance
router.include_router links
Depends(...) references
HTTPException raise sites
exception handlers
middleware registrations
```

Outputs:

```text
atlas/index/import-index.yaml
atlas/runtime/dependency-map.yaml
atlas/runtime/router-inclusion-map.yaml
atlas/runtime/middleware-map.yaml
atlas/errors/python-exception-map.yaml
```

## 3. OpenSearch payload reconstruction

Build Layer 1.5 before business-rule derivation.

Outputs:

```text
atlas/payloads/opensearch-query-dsl.yaml
atlas/payloads/generated-query-builders.yaml
atlas/graph/payload-graph.yaml
```

Required behaviour:

```text
capture literal query bodies
track dict/list assignments
resolve local variables used in search(body=...)
mark unresolved runtime variables explicitly
link query builders to data-access functions and indexes
```

## 4. Local knowledge database

Keep YAML/JSON canonical for reviews and diffs. Compile a fast read model for ngk.

Recommended order:

```text
SQLite first: dependency-free relational lookups.
DuckDB second: analytics over large Atlas outputs.
Kuzu later: graph-native traversal if ngk trace/impact queries need Cypher-style querying.
```

Outputs:

```text
atlas/knowledge/atlas.sqlite
atlas/knowledge/atlas.duckdb
atlas/knowledge/atlas.kuzu
```

## 5. ngk trace

Use `atlas/tools/ngk_trace_regraph_exporter.py` as the file-based first implementation.

Future path:

```text
ngk trace "POST /claims"
→ query atlas.sqlite/duckdb/kuzu if available
→ fall back to YAML/JSON files
→ emit ReGraph payload
→ open visualizer or write payload path
```

## 6. Kiro task breakdown

Implement in small tasks:

```text
1. Add ts-morph indexer for imports/routes/TanStack/Leaflet/ReGraph.
2. Add Python import resolver and FastAPI router inclusion mapper.
3. Add OpenSearch query DSL reconstructor for dict/list builders.
4. Add error-flow mapper for Python and React.
5. Add SQLite knowledge compiler.
6. Wire ngk trace to ReGraph exporter.
7. Add validation and adversarial review for each layer.
```
