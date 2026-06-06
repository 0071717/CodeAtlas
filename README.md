# CodeAtlas

CodeAtlas is a deterministic-first framework for reverse-engineering mature codebases into evidence-backed, machine-readable project knowledge for AI coding agents, developer CLIs, reviewers, test generators, and visualisation tools.

It is designed for ecosystems like:

- React / TypeScript frontends
- FastAPI / Pydantic backends
- OpenSearch/data-access layers
- multi-repo config/schema/sample-data setups
- file-system-only AI workflows where MCP is disabled
- Kiro CLI and custom developer CLIs such as `ngk`

## Canonical status

**The V2 deterministic path is canonical.**

The older prompt-first Kiro extraction pipeline remains in the repository as legacy/exploratory material, but it should not be the default first run for a new project.

Start with:

```bash
python3 atlas/tools/codeatlas_v2_canonical.py doctor
python3 atlas/tools/codeatlas_v2_canonical.py all
```

or:

```bash
bash atlas/scripts/run-pre-transfer-check.sh
bash atlas/scripts/run-framework-v2-suite.sh
```

Then use targeted Kiro/AI enrichment only after deterministic artifacts exist.

## Core model

CodeAtlas behaves like a compiler for project knowledge:

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

The goal is not to make AI reread the whole application with different prompts. The goal is to generate stable file/symbol/route/endpoint/payload/flow/test artifacts that AI agents and tools can safely consume.

## Read first

For Kiro and future maintainers:

```text
docs/CANONICAL_EXECUTION_PATH.md
docs/LEGACY_AND_EXPERIMENTAL_PATHS.md
docs/PRE_TRANSFER_READINESS_CHECKLIST.md
docs/KIRO_ZIP_HANDOFF.md
docs/FRAMEWORK_ARCHITECTURE_V2.md
docs/LAYER_BUILD_CONTRACT.md
docs/KIRO_FRAMEWORK_IMPLEMENTATION_GUIDE.md
docs/NGK_ECOSYSTEM_HARDENING_PLAN.md
docs/NGK_TRACE_VISUAL_FLOW_EXPLORER.md
docs/TOOL_SUITE_V2.md
docs/CHANGELOG.md
docs/ROADMAP_AND_IMPLEMENTATION_PLAN.md
docs/REPO_CLEANUP_POLICY.md
```

For older/legacy concepts:

```text
docs/KNOWLEDGE_CONTEXT_LAYER.md
docs/CODE_MAP_FOUNDATION.md
docs/YAML_CONTRACT.md
docs/WORKFLOW.md
docs/MAINTENANCE_STRATEGY.md
```

## What CodeAtlas produces

| Layer | Why it exists |
|---|---|
| `atlas/source/` | Source snapshots, repo manifests, file hashes, provenance |
| `atlas/index/` | Deterministic file/symbol/endpoint/route/API/test/config indexes |
| `atlas/payloads/` | Request/response/OpenSearch Query DSL reconstruction |
| `atlas/bindings/` | Ecosystem bindings for libraries such as Leaflet, ReGraph, TanStack Query, Material UI, OpenSearch, and `ngk` |
| `atlas/runtime/` | Middleware, dependencies, exception handlers, auth/config envelopes |
| `atlas/graph/` | Nodes, edges, contracts, payload graph, error graph, test graph |
| `atlas/errors/` | Python and frontend error/exception maps |
| `atlas/flows/` | API request flows, UI action flows, error flows, data flows |
| `atlas/facts/` | Objective technical facts derived from deterministic evidence |
| `atlas/rules/` | Technical and business rules derived from facts |
| `atlas/requirements/` | Optional user stories, acceptance criteria, epics, HLRs |
| `atlas/testing/` | Test inventory, fixture/mock maps, coverage gaps, test candidates |
| `atlas/knowledge/` | Normalized nodes, edges, indexes, graph exports, cards, optional local DB read models |
| `atlas/audit/` | Validation, reverse verification, unsupported claims, stale artifacts |
| `atlas/change/` | Changed files/symbols, impacted nodes/flows/tests, targeted rerun plans |
| `atlas/visualizer/` | ReGraph/Cytoscape/force-graph-ready exports |

## Important design rules

1. Source code is the authority for current behaviour.
2. Deterministic artifacts come before AI enrichment.
3. AI-derived claims must cite evidence or use `needs_review: true`.
4. Frontend-only validation is not backend enforcement.
5. Backend-only endpoints are not dead code without evidence.
6. OpenSearch Query DSL must be reconstructed or marked unresolved; do not invent clauses.
7. Error paths are first-class flows, not notes.
8. Generated artifacts must be validation-friendly, reviewable, and diffable.
9. The legacy prompt-first path is not the default first run.
10. If Atlas and source code disagree, mark Atlas stale or unsupported.

## `ngk trace`

CodeAtlas includes a first file-based ReGraph exporter:

```bash
python3 atlas/tools/ngk_trace_regraph_exporter.py "POST /claims"
```

It writes:

```text
atlas/visualizer/ngk-trace/<trace-id>.regraph.json
atlas/visualizer/ngk-trace/<trace-id>.summary.md
```

The long-term `ngk trace` flow should resolve:

```text
React UI Action
→ API Client
→ FastAPI Router
→ Dependency/Middleware
→ Service Layer
→ OpenSearch Query DSL
→ Response/Error UI State
```

## Current maturity

CodeAtlas is a framework under active hardening. The V2 deterministic foundation exists, but some deeper extractors are still planned:

```text
TypeScript AST / ts-morph extraction
FastAPI router/dependency materialisation
OpenSearch Query DSL reconstruction
explicit Python/React error-flow extraction
symbol-level drift planning
SQLite/DuckDB/Kuzu read models
```

Do not treat upper requirement layers as equally mature as source/index/graph layers until those lower extractors are validated.

## Pre-transfer check

Before copying CodeAtlas into a restricted Kiro network:

```bash
python3 atlas/tools/codeatlas_v2_canonical.py doctor
```

Review:

```text
atlas/audit/preflight-doctor-report.json
atlas/audit/artifact-json-promotion-report.json
```

See:

```text
docs/PRE_TRANSFER_READINESS_CHECKLIST.md
```
