# No-MCP Local Memory Design

This document defines the CodeAtlas strategy for using persistent code-memory ideas when MCP is unavailable and assumed to remain unavailable.

## Decision

CodeAtlas must not depend on MCP.

MCP-style graph tools are useful as an interaction pattern, but CodeAtlas implements the pattern through local files, SQLite, and CLI commands:

```text
deterministic extraction
→ canonical JSON/YAML artifacts
→ capability-gap audit
→ SQLite read model
→ context-pack JSON/Markdown
→ Kiro/ngk prompt context
```

## Adapted strategy

Persistent code-memory systems usually follow this shape:

```text
parse source files
→ build knowledge graph
→ store graph locally
→ expose graph tools to the LLM
```

CodeAtlas keeps the first three parts and replaces the final MCP tool surface with generated context packs.

| Persistent-memory idea | CodeAtlas no-MCP adaptation |
|---|---|
| Tree-sitter/AST parsing | Python AST, regex seeds, future ts-morph/tree-sitter extractors |
| Knowledge graph | `atlas/graph/nodes.json`, `atlas/graph/edges.json` |
| SQLite graph store | `atlas/knowledge/atlas.sqlite` generated read model |
| MCP query tools | `codeatlas_context_pack.py search/build/trace/impact` |
| Agent tool loop | `ngk` pre-builds a context pack before calling Kiro/LLM |
| Incremental re-indexing | `atlas/change/*` drift reports and targeted rerun plans |
| Call tracing | graph edge expansion plus trace context packs |
| Impact analysis | file/symbol matching plus inbound/outbound edge expansion |
| Hub/orphan visibility | graph report and visualizer exports |
| Unknown semantics | capability-gap reports and `needs_review` flags |

## Implemented tools

### Capability audit

```bash
python3 atlas/tools/codeatlas_capability_audit.py
```

Outputs:

```text
atlas/bindings/library-capabilities.json
atlas/audit/capability-gaps.json
atlas/audit/unsupported-capabilities.json
```

Purpose:

```text
detect known supported imports
detect unknown import roots
separate stdlib/internal/relative imports from likely external libraries
create binding stubs for review
tell context packs where Atlas must not infer semantics
```

### SQLite read model

```bash
python3 atlas/tools/codeatlas_sqlite_read_model.py
```

Outputs:

```text
atlas/knowledge/atlas.sqlite
atlas/knowledge/sqlite-compile-report.json
```

Tables:

```text
metadata
nodes
edges
facts
flows
capability_gaps
cards
cards_fts, when SQLite FTS5 is available
```

The SQLite file is generated and disposable. Canonical truth remains in JSON/YAML artifacts.

### Context packs

```bash
python3 atlas/tools/codeatlas_context_pack.py search "claims endpoint"
python3 atlas/tools/codeatlas_context_pack.py build "why does claims search ignore archived records?"
python3 atlas/tools/codeatlas_context_pack.py trace "POST /claims"
python3 atlas/tools/codeatlas_context_pack.py impact backend/app/routes/claims.py
```

Outputs:

```text
atlas/context-packs/<mode>.<query>.json
atlas/context-packs/<mode>.<query>.md
```

Each context pack contains:

```text
query and mode
selected cards
selected graph nodes
selected graph edges
selected facts
selected flows
evidence files/lines
capability warnings
known unknowns
LLM instructions
```

## Missing-library policy

Atlas does not need complete library knowledge to be useful. It does need complete honesty about what it understands.

When Atlas sees an unknown library:

```text
it may index files, imports, symbols, generic calls, and local evidence
it may include the affected files in graph/context packs
it must mark the library as an unsupported capability gap
it must not infer framework-specific behavior for that library
```

Examples:

| Unknown library type | Atlas must avoid inferring |
|---|---|
| Router/navigation library | route graph, navigation side effects |
| State-management library | state machine, cache invalidation, persistence |
| Form library | validation behavior, submission lifecycle |
| Auth/permission library | backend enforcement, frontend-only checks |
| Data-fetching library | retries, caching, mutation invalidation |
| Visualization library | rendered node/map semantics |

The right fix is to add a reviewed binding and, where needed, a deterministic extractor.

## `ngk` integration contract

`ngk` should treat context-pack generation as a required pre-step before asking an LLM about a codebase.

Recommended flows:

```bash
ngk atlas build
  → python3 atlas/tools/codeatlas_v2_canonical.py all

ngk ask "why does claims search ignore archived records?"
  → python3 atlas/tools/codeatlas_context_pack.py build "<question>"
  → pass atlas/context-packs/build.<question>.json to Kiro/LLM

ngk trace "POST /claims"
  → python3 atlas/tools/codeatlas_context_pack.py trace "POST /claims"
  → python3 atlas/tools/ngk_trace_regraph_exporter.py "POST /claims"

ngk impact backend/app/routes/claims.py
  → python3 atlas/tools/codeatlas_context_pack.py impact backend/app/routes/claims.py
```

## Confidence rules

```text
high confidence: directly parsed source evidence and exact graph links
medium confidence: deterministic heuristic with review metadata
low confidence: unresolved dynamic behavior or weak string/regex match
needs_review: true whenever a claim depends on unsupported libraries, unresolved dispatch, unknown payload shape, or incomplete route/client matching
```

## What this does not solve yet

```text
full TypeScript type-aware resolution
framework-specific semantics for every UI/API dependency
runtime-only behavior
dynamic import/plugin systems
complete OpenSearch query reconstruction
full branch-aware flow graphs
```

These are extractor problems, not MCP problems. MCP would not make unsupported semantics safe; it would only expose unsafe assumptions faster. CodeAtlas should prefer conservative local artifacts over a tool surface that hides uncertainty.
