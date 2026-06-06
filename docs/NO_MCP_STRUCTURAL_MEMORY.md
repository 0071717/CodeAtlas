# No-MCP Structural Memory Design

This document adapts the useful persistent-code-memory strategies to CodeAtlas while assuming MCP remains disabled.

The key rule is simple: **MCP is transport, not architecture**. CodeAtlas must keep the durable parts — deterministic extraction, persistent structural graph memory, fast local queries, call-path tracing, impact analysis, source snippets, stale-index checks, and context-pack generation — but expose them through files and CLI commands instead of an MCP server.

## Canonical restricted-network path

```text
source repositories
→ deterministic CodeAtlas artifacts
→ capability-gap audit
→ local SQLite read model
→ no-MCP context packs
→ Kiro/ngk prompt context
```

No step may require an MCP server, tool registry, JSON-RPC process, socket, daemon, browser extension, or network service.

## Commands

Run the deterministic foundation first:

```bash
python3 atlas/tools/codeatlas_v2_canonical.py all
```

The canonical runner now builds the no-MCP memory layer as part of `all`. The stages can also be run directly:

```bash
python3 atlas/tools/codeatlas_v2_canonical.py capability-audit
python3 atlas/tools/codeatlas_v2_canonical.py sqlite-read-model
python3 atlas/tools/codeatlas_v2_canonical.py no-mcp-memory
```

Then build task-specific packs:

```bash
python3 atlas/tools/codeatlas_context_pack.py search "claims endpoint"
python3 atlas/tools/codeatlas_context_pack.py build "why does claims search ignore archived records?"
python3 atlas/tools/codeatlas_context_pack.py trace "POST /claims"
python3 atlas/tools/codeatlas_context_pack.py impact backend/app/routes/claims.py
```

## What gets generated

```text
atlas/bindings/library-capabilities.json
atlas/audit/capability-gaps.json
atlas/audit/unsupported-capabilities.json
atlas/knowledge/atlas.sqlite
atlas/knowledge/sqlite-compile-report.json
atlas/context-packs/*.json
atlas/context-packs/*.md
```

JSON/YAML artifacts remain the source of truth. SQLite is a compiled read model for fast local lookups.

## Unknown-library policy

Atlas may index files that use unknown libraries, but it must not invent semantics for those libraries.

Correct behavior:

```text
unknown import
→ still index file/import/symbol/call candidates
→ mark capability gap
→ lower confidence on affected facts/flows
→ include the gap in context packs
→ require a binding or direct source evidence before framework-specific claims
```

Examples of claims Atlas must not infer from unknown libraries alone:

```text
cache behavior
state lifecycle
routing semantics
permission semantics
form validation semantics
query invalidation
OpenSearch/query-contract meaning
```

## SQLite read model

The SQLite read model should contain enough structure for local tools and `ngk` wrappers to answer common structural questions without re-reading the whole repo:

```text
nodes
edges
facts
flows
capability_gaps
cards / FTS cards when available
```

It is allowed to be rebuilt at any time from canonical artifacts. It should not contain hand-edited source of truth.

## Context packs

Context packs are the no-MCP replacement for an agent repeatedly deciding which tools to call.

A good context pack includes:

```text
user question or task
selected nodes
selected edges
selected facts
selected flows
evidence files and line ranges
capability warnings
known unknowns
drift or validation warnings
LLM instructions
```

Kiro/ngk should receive the context pack before broad raw-source exploration. Raw source fallback is still allowed when evidence is missing, stale, or explicitly requested, but broad source scans should not be the first move.

## Relationship to Codebase-Memory-style systems

The reusable idea is the persistent local code graph and typed query layer. The non-reusable assumption is MCP as the only interface.

CodeAtlas uses this split:

```text
keep:
  persistent structural memory
  call-path traversal
  impact analysis
  architecture summaries
  source snippets
  stale-index checks
  query/search context building

replace:
  MCP tool server
  agent tool registry dependency
  background daemon requirement

with:
  local CLI commands
  reviewable JSON/Markdown artifacts
  SQLite read model
  ngk/Kiro context-pack handoff
```

## Acceptance criteria

The no-MCP memory layer is acceptable when:

```text
python3 atlas/tools/codeatlas_v2_canonical.py all builds artifacts and local memory
python3 atlas/tools/codeatlas_v2_canonical.py no-mcp-memory rebuilds capability gaps and SQLite only
context packs can be produced without network or MCP access
unknown libraries appear in audit/context outputs instead of being ignored
SQLite can be deleted and regenerated from canonical artifacts
```
