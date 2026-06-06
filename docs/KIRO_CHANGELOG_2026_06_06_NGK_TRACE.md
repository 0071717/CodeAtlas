# Kiro Changelog — 2026-06-06 ngk Trace and Fractional Layers

## Summary

CodeAtlas V2 now includes explicit fractional-layer architecture for:

```text
Layer 1.5 — Data payload and DSL reconstruction
Layer 3.5 — Ecosystem and third-party bindings
Layer 5.5 — Explicit error and exception flows
```

These layers reduce AI hallucination by capturing OpenSearch payloads, third-party semantic roles, and error paths before full flow and rule derivation.

## Added / updated

- Updated `docs/FRAMEWORK_ARCHITECTURE_V2.md` with fractional layers and optional local knowledge databases.
- Updated `docs/LAYER_BUILD_CONTRACT.md` with fractional-layer acceptance criteria.
- Added `atlas/config/ecosystem-bindings.yaml` for ngk, React Router, TanStack Query, Leaflet, ReGraph, Material UI, and OpenSearch.
- Added `docs/NGK_TRACE_VISUAL_FLOW_EXPLORER.md`.
- Added `docs/NGK_ECOSYSTEM_HARDENING_PLAN.md`.
- Added `atlas/tools/ngk_trace_regraph_exporter.py`.

## New command blueprint

```bash
python3 atlas/tools/ngk_trace_regraph_exporter.py "POST /claims"
```

The exporter reads graph, flow, payload, error, and testing artifacts and emits:

```text
atlas/visualizer/ngk-trace/<trace-id>.regraph.json
atlas/visualizer/ngk-trace/<trace-id>.summary.md
```

## Next implementation tasks

1. Build a ts-morph TypeScript indexer for React Router, TanStack Query, Leaflet, ReGraph, API clients, and error states.
2. Build a Python import resolver for FastAPI dependencies and router inclusion tracing.
3. Build OpenSearch Query DSL reconstruction for query builder functions.
4. Build explicit Python/React error-flow extraction.
5. Compile `atlas/knowledge` into SQLite first, then optionally DuckDB or Kuzu.
