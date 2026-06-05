# Kiro Framework Implementation Guide

This guide tells Kiro how to extend CodeAtlas itself.

CodeAtlas V2 should be built like a deterministic compiler pipeline with bounded AI enrichment, not as a sequence of large unverified prompts.

## Implementation principles

1. Build deterministic tools first.
2. Use AI for bounded semantic enrichment only.
3. Every layer must have declared inputs, outputs, schemas, validators, and known limitations.
4. Preserve stable IDs across reruns.
5. Every claim must include evidence or `needs_review: true`.
6. Source code wins over generated Atlas artifacts.
7. Prefer targeted reruns over full regeneration.
8. Never silently fix unsupported claims; emit verification findings.
9. Do not modify application repos unless the user explicitly asks.
10. Build small composable scripts rather than one monolithic extractor.

## Kiro work pattern

For every framework change, follow this loop:

```text
discover
→ plan bounded task
→ implement smallest useful tool/prompt/schema
→ run validation
→ document limitations
→ update changelog
→ add next task recommendations
```

Do not attempt to complete the entire framework in one pass.

## What to build first

### Phase 1 — deterministic foundation

```text
source snapshotter
file hash and line-count indexer
file classifier
symbol indexer
YAML/JSON parse validator
link validator
visualizer data exporter
```

### Phase 2 — framework extractors

```text
Python AST symbol indexer
FastAPI endpoint extractor
Pydantic schema extractor
FastAPI middleware/dependency/exception handler extractor
TypeScript/React symbol extractor
React route/component/hook/API client extractor
existing test inventory extractor
OpenSearch/config extractor
GitLab CI extractor
sample-data generator extractor
```

### Phase 3 — graph and flow builders

```text
relationship graph builder
contract graph builder
API request flow builder
UI state/interaction flow builder
data/error/permission flow builders
```

### Phase 4 — maintenance and tooling

```text
drift checker
targeted rerun planner
PR/MR impact analyzer
test gap analyzer
Playwright/API test planners
debug navigator
visualizer exporter/UI
context pack generator
```

## Deterministic vs AI-driven work

### Mostly deterministic

```text
file scan
hashing
line counts
language classification
AST symbol extraction
route/endpoint discovery
basic call extraction
schema parse validation
ID/link validation
changed-file detection
visualizer export
```

### Hybrid

```text
semantic map enrichment
permission/validation/error mapping
middleware/runtime envelope mapping
API/UI flow building
contract mapping
test coverage mapping
```

### Mostly AI-assisted

```text
domain naming
responsibility summaries
technical fact wording
business rule derivation
user stories and acceptance criteria
test scenario descriptions
UI/UX critique
adversarial challenge review
MR review comments
```

## Kiro implementation rules

When implementing a layer or tool:

```text
1. Read the relevant docs and layer contract.
2. Define exact artifacts to read and write.
3. Add or update a small script under `atlas/tools/` or `atlas/scripts/`.
4. Keep output JSON/YAML stable and diffable.
5. Add `confidence` and `needs_review` where interpretation is involved.
6. Add validator output under `atlas/audit/`.
7. Avoid adding dependencies unless there is clear value.
8. If a dependency is optional, provide a standard-library fallback.
9. Include a dry-run or plan output before mutating application repos.
10. Update `docs/KIRO_CHANGELOG.md`.
```

## What Kiro should not do

```text
Do not read the whole app and invent requirements in one pass.
Do not build downstream tools by rescanning raw code when Atlas artifacts already exist.
Do not use giant YAML dumps as prompt context.
Do not mark AI-inferred claims as high confidence without evidence.
Do not treat frontend-only validation as authoritative backend enforcement.
Do not treat backend-only endpoints as dead code without evidence.
Do not post MR comments without explicit approval.
```

## Definition of done

A framework task is done when:

```text
output artifacts exist
schema/parse validation passes or findings are documented
limitations are explicit
runner command is documented
changelog is updated
Kiro knows the next targeted task
```
