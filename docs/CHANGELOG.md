# CodeAtlas Changelog

Canonical changelog for CodeAtlas framework evolution.

This file preserves the relevant content from retired standalone files so the repo has fewer stale entrypoints without losing historical context.

## From `docs/KIRO_CHANGELOG.md`

## Kiro Changelog

This changelog is written for Kiro, future AI agents, and humans maintaining CodeAtlas.

### 2026-06-05 — V2 deterministic framework foundation

#### Summary

CodeAtlas now has a V2 architecture and first deterministic tool suite. The framework direction is now compiler-like: source snapshot → deterministic indexes → graph/flow seeds → validation/drift reports → visualizer exports → AI enrichment only where useful.

This update deliberately uses readable Python source. Do not reintroduce encoded/base64 payload launchers; Kiro and humans must be able to inspect and modify framework tools directly.

#### Added docs

- `docs/FRAMEWORK_ARCHITECTURE_V2.md`
  - Defines V2 planes: source/provenance, structural index, runtime entrypoint, semantic architecture, runtime context, graph/contracts, conditional flows, facts, rules, testing, knowledge, verification, tooling, and targeted reruns.

- `docs/KIRO_ZIP_HANDOFF.md`
  - Instructions for Kiro when CodeAtlas is supplied as a zip, copied workspace, or fresh clone.

- `docs/KIRO_FRAMEWORK_IMPLEMENTATION_GUIDE.md`
  - Tells Kiro how to build CodeAtlas in bounded deterministic tasks.

- `docs/LAYER_BUILD_CONTRACT.md`
  - Defines required inputs, outputs, schemas, validators, confidence policy, and rerun policy for each layer.

- `docs/AST_EXTRACTION_STRATEGY.md`
  - Explains how to use AST/parsers to produce reduced semantic indexes instead of raw AST dumps.

- `docs/MULTI_REPO_MAPPING_STRATEGY.md`
  - Defines multi-repo support for frontend, backend, shared contracts, OpenSearch/config, sample-data, test-support, and docs repos.

- `docs/RUNTIME_CONTEXT_MAPPING.md`
  - Defines middleware/dependency/exception/auth/logging/config mapping for runtime envelopes.

- `docs/TESTING_ARCHAEOLOGY.md`
  - Defines how to map existing weak tests, fixtures, mocks, and gaps before generating new tests.

- `docs/VERIFICATION_AND_CHALLENGE_LAYER.md`
  - Defines parse/link/source/contract/flow validation and adversarial claim review.

- `docs/TARGETED_RERUN_ENGINE.md`
  - Defines changed file → impacted node/flow/rule/test → targeted rerun strategy.

- `docs/UI_UX_IMPLEMENTATION_GUIDE.md`
  - Gives Kiro UI/UX rules, UI state checklist, and visualizer guidance.

- `docs/TOOL_SUITE_V2.md`
  - Documents the first deterministic suite commands and current limitations.

#### Added tools

- `atlas/tools/codeatlas_v2_suite.py`
  - Plain Python deterministic foundation suite.
  - Provides `init`, `snapshot`, `index`, `graph`, `validate`, `drift-check`, `visualizer-export`, and `all` commands.
  - Produces source snapshots, file hashes, file/symbol/endpoint/route/API-client/test indexes, graph seeds, API-flow seeds, validation reports, drift reports, and visualizer JSON.

- `atlas/scripts/run-framework-v2-suite.sh`
  - Simple runner for the V2 suite.

#### Added framework prompts

- `atlas/prompts/framework/00-discovery-planner.md`
- `atlas/prompts/framework/02-layer-implementation-worker.md`
- `atlas/prompts/framework/04-validator-worker.md`
- `atlas/prompts/framework/05-adversarial-reviewer.md`
- `atlas/prompts/framework/07-ui-ux-worker.md`
- `atlas/prompts/framework/08-test-archaeology-worker.md`

#### Important behaviour changes

Kiro should prefer deterministic tools before AI interpretation.

Kiro should run:

```bash
python3 atlas/tools/codeatlas_v2_suite.py all
```

or:

```bash
bash atlas/scripts/run-framework-v2-suite.sh
```

for the first V2 foundation pass.

Kiro should no longer expect encoded launcher payloads. The V2 suite lives as readable Python source.

CI/CD extraction is intentionally out of scope for now.

#### Recommended next tasks

1. Refactor `codeatlas_v2_suite.py` into smaller modules under `atlas/tools/`.
2. Add stronger Python AST extraction for Pydantic schemas, FastAPI dependencies, middleware, and exception handlers.
3. Add stronger TypeScript/React extraction using a real TypeScript parser when available.
4. Add branch-aware API request flow generation.
5. Add UI state/interaction flow generation.
6. Add OpenSearch/config extractor.
7. Add fixture/mock/test archaeology extraction.
8. Add richer visualizer exporter and then build the visualizer UI.

### 2026-06-05 — Knowledge context, reverse verification, and MR review framework

#### Summary

CodeAtlas now has a stronger post-extraction workflow for turning generated maps/rules/requirements into a normalized machine-readable knowledge layer, verifying generated claims back against code, refreshing Kiro context, and preparing safe GitLab merge-request reviews.

#### Added

- `docs/KNOWLEDGE_CONTEXT_LAYER.md`
  - Defines `atlas/knowledge/` as the normalized machine-readable layer above generated Atlas outputs.
  - Defines canonical node, edge, index, graph, card, and audit structures.
  - Defines AI context priority for Kiro and future agents.

- `docs/CODE_ATLAS_REVERSE_VERIFICATION.md`
  - Defines Code ↔ Atlas reverse verification.
  - Checks generated maps, facts, rules, stories, and requirements back against source evidence.
  - Adds stale evidence, unsupported claim, invalid evidence, and targeted rerun concepts.

- `docs/MERGE_REQUEST_REVIEW_FRAMEWORK.md`
  - Defines GitLab merge-request review workflow using `glab`.
  - Defaults to draft-only review.
  - Requires explicit approval before posting comments.
  - Requires all AI-generated comments to start with `✦ AI GENERATED REVIEW`.
  - Prefers inline comments where line context exists.

- `docs/KIRO_CONTEXT_USAGE.md`
  - Explains how Kiro should use `atlas/knowledge`, context packs, steering files, generated YAML, and source code.
  - Defines context priority and task-specific guidance for debugging, feature work, refactoring, tests, and MR reviews.

- `atlas/prompts/30-knowledge-normalizer.md`
  - Kiro prompt to normalize existing generated Atlas outputs into `atlas/knowledge/`.

- `atlas/prompts/31-reverse-verification.md`
  - Kiro prompt to verify generated Atlas claims back against code and traceability evidence.

- `atlas/prompts/32-kiro-context-refresh.md`
  - Kiro prompt to refresh context packs and `.kiro/steering` from normalized knowledge.

- `atlas/prompts/33-merge-request-review.md`
  - Kiro prompt for safe GitLab MR review using CodeAtlas context.

- `atlas/scripts/run-knowledge-normalizer.sh`
  - Runs prompt 30.

- `atlas/scripts/run-reverse-verification.sh`
  - Runs prompt 31.

- `atlas/scripts/run-context-refresh.sh`
  - Runs prompt 32.

- `atlas/scripts/run-mr-review.sh`
  - Runs prompt 33 for a GitLab MR IID.
  - Defaults to no comment posting.

- `atlas/scripts/run-post-extraction-suite.sh`
  - Runs normalization, reverse verification, and context refresh in sequence.

#### Updated agents

- `.kiro/agents/atlas-forge.json`
  - Now prefers `atlas/knowledge` first.
  - Includes MR review safety guidance.

- `.kiro/agents/atlas-cartographer.json`
  - Now checks knowledge indexes, reverse-verification findings, stale-map candidates, and unsupported claims before map/fact changes.

- `.kiro/agents/domain-scout.json`
  - Now uses domain-relevant knowledge nodes, cards, edges, and reverse-verification findings before domain extraction/refresh.

- `.kiro/agents/rift-hunter.json`
  - Now explicitly handles reverse verification, unsupported claims, and stale generated artifacts.

- `.kiro/agents/memory-smith.json`
  - Now refreshes context packs and steering files from `atlas/knowledge`.

#### Important behaviour changes

Kiro should now prefer this context order:

1. `atlas/knowledge/manifest.yaml`
2. `atlas/knowledge/indexes/*.yaml`
3. `atlas/knowledge/cards/*.json`
4. `atlas/context-packs/*.md`
5. `.kiro/steering/*.md`
6. `atlas/knowledge/nodes/*.yaml`
7. `atlas/knowledge/edges.yaml`
8. `atlas/knowledge/audit/*.md`
9. original `atlas/map`, `atlas/facts`, and `atlas/domains` artifacts
10. raw source code, only when needed

If source code and generated Atlas context disagree, Kiro should trust source code and mark the generated Atlas artifact stale or unsupported.

#### Recommended next command in an existing workspace

After pulling these framework changes into a workspace that already has generated Atlas artifacts:

```bash
bash atlas/scripts/run-post-extraction-suite.sh
```

This should:

1. normalize generated outputs into `atlas/knowledge/`,
2. reverse-check generated claims against code evidence,
3. refresh Kiro context packs and `.kiro/steering` files.

#### Note about executable bits

Files created through GitHub's contents API may not retain executable permissions. If running scripts with `./atlas/scripts/...` fails, run:

```bash
chmod +x atlas/scripts/*.sh
```

or invoke scripts with `bash atlas/scripts/<script>.sh`.

## From `docs/KIRO_CHANGELOG_V2_TOOLING.md`

## Kiro Changelog Addendum — V2 Tooling Improvements

This addendum records the latest deterministic tooling improvements for Kiro.

### 2026-06-05 — Improved readable Python V2 suite

#### Changed

- `atlas/tools/codeatlas_v2_suite.py` was expanded as readable Python source.
- The suite now uses deterministic file scanning, hashing, AST parsing, graph building, flow seeding, drift reporting, validation, and visualizer export.
- Encoded payload launchers are no longer part of the active suite.

#### New or improved outputs

```text
atlas/source/snapshot.yaml
atlas/source/file-hashes.yaml
atlas/index/file-index.yaml
atlas/index/symbol-index.yaml
atlas/index/import-index.yaml
atlas/index/endpoint-index.yaml
atlas/index/route-index.yaml
atlas/index/component-index.yaml
atlas/index/hook-index.yaml
atlas/index/api-client-index.yaml
atlas/index/schema-index.yaml
atlas/index/service-index.yaml
atlas/index/data-access-index.yaml
atlas/index/runtime-entrypoint-index.yaml
atlas/index/ui-action-index.yaml
atlas/index/test-index.yaml
atlas/index/config-index.yaml
atlas/runtime/runtime-map.yaml
atlas/testing/test-inventory.yaml
atlas/graph/nodes.yaml
atlas/graph/edges.yaml
atlas/flows/api-request-flows.yaml
atlas/flows/ui-flows.yaml
atlas/audit/v2-validation-report.yaml
atlas/change/changed-files.yaml
atlas/change/impacted-nodes.yaml
atlas/change/impacted-edges.yaml
atlas/change/targeted-rerun-plan.yaml
atlas/visualizer/graph-data.json
atlas/visualizer/cytoscape-elements.json
atlas/visualizer/node-detail-index.json
atlas/visualizer/flow-cards.json
```

#### Added framework prompts

```text
atlas/prompts/framework/09-visualizer-builder.md
atlas/prompts/framework/10-opensearch-config-worker.md
```

#### What Kiro should do next

Run:

```bash
python3 atlas/tools/codeatlas_v2_suite.py all
```

Then inspect:

```text
atlas/audit/v2-validation-report.yaml
atlas/source/snapshot.yaml
atlas/index/
atlas/graph/
atlas/flows/
atlas/visualizer/
```

#### Known limitations

- TypeScript/React extraction is still regex-based and should later use a real parser.
- FastAPI router prefix handling is not complete.
- API flow branches are seeded from AST if-statements but not yet full symbolic execution.
- UI flows are route/API-call seeds, not complete state machines yet.
- OpenSearch/config extraction is only file/config indexing so far.

## From `docs/KIRO_CHANGELOG_V2_AI_ASSISTED.md`

## Kiro Changelog — V2 AI-Assisted Extraction Update

This file supplements `docs/KIRO_CHANGELOG.md` for the AI-assisted extraction improvements.

### 2026-06-05 — AI-assisted bounded extraction and React stack mapping

#### Summary

CodeAtlas V2 now explicitly supports a hybrid extraction strategy:

```text
deterministic foundation first
→ bounded AI-assisted enrichment
→ validation and adversarial review
→ targeted next tasks
```

The intent is to move faster without waiting for perfect TypeScript or Python parser coverage, while still keeping evidence, confidence, and `needs_review` discipline.

#### Added docs

- `docs/AI_ASSISTED_EXTRACTION_STRATEGY.md`
  - Defines when AI-assisted extraction is appropriate.
  - Requires bounded source slices, evidence, confidence, and validation.

- `docs/REACT_UI_STACK_MAPPING.md`
  - Specializes UI extraction for React, TypeScript, React Router DOM, TanStack Query, and Material UI.
  - Defines route, query, mutation, MUI form/action/state, and UI flow mapping targets.

- `docs/TASK_DECOMPOSITION_PLAYBOOK.md`
  - Defines how to break extraction/tooling work into small Kiro-executable tasks.

#### Added prompts

- `atlas/prompts/framework/09-ai-assisted-extraction-worker.md`
- `atlas/prompts/framework/10-react-stack-ui-mapper.md`
- `atlas/prompts/framework/11-bounded-backend-flow-mapper.md`
- `atlas/prompts/framework/12-task-slicer.md`

#### Updated guidance

- `docs/KIRO_ZIP_HANDOFF.md`
  - Now tells Kiro to read the AI-assisted extraction strategy, React stack mapping guide, and task decomposition playbook.
  - Adds current frontend assumptions: React, TypeScript, React Router DOM, TanStack Query, and Material UI.

#### Recommended next workflow

1. Run the deterministic V2 foundation suite.
2. Pick one UI route/page cluster.
3. Run the React stack UI mapper prompt on that slice.
4. Pick the linked backend endpoint.
5. Run the bounded backend flow mapper prompt.
6. Validate outputs.
7. Run adversarial review.
8. Generate test candidates for that single route/API flow pair.

#### Important note

AI-assisted extraction is allowed, but it is not automatically trusted. Claims still need evidence, confidence, `needs_review`, and validation.

## From `docs/KIRO_CHANGELOG_V2_REACT_STACK_INDEXER.md`

## Kiro Changelog — V2 React Stack Indexer

### 2026-06-05 — React Router, TanStack Query, and Material UI candidate indexer

#### Added tool

- `atlas/tools/react_stack_candidate_indexer.py`
  - Plain Python heuristic indexer for frontend repos using React Router DOM, TanStack Query, and Material UI.
  - Produces stack-specific candidate artifacts for bounded AI-assisted mapping.

#### Added runner

- `atlas/scripts/run-react-stack-indexer.sh`

#### Added docs

- `docs/REACT_STACK_INDEXER_TOOL.md`
  - Documents command, outputs, stack-specific targets, confidence policy, and recommended sequence.

#### Outputs

```text
atlas/index/react-router-index.yaml
atlas/index/tanstack-query-index.yaml
atlas/index/material-ui-index.yaml
atlas/map/ui-state-candidates.yaml
atlas/audit/react-stack-indexer-report.yaml
```

#### Recommended use

Run after the V2 foundation suite:

```bash
python3 atlas/tools/codeatlas_v2_suite.py all
python3 atlas/tools/react_stack_candidate_indexer.py
```

Then run the React stack UI mapper prompt on one route/page cluster.

## From `docs/KIRO_CHANGELOG_V2_CONTRACT_TESTING.md`

## Kiro Changelog — V2 Contract and Testing Workers

This supplements the main Kiro changelog.

### 2026-06-05 — Contract mapper and UI-flow test worker

#### Added prompts

- `atlas/prompts/framework/13-ui-api-contract-mapper.md`
  - Maps one frontend API client or TanStack Query hook to one backend endpoint candidate.
  - Writes contract graph, UI-to-API graph, API/schema maps, and mismatch findings.

- `atlas/prompts/framework/14-playwright-from-ui-flow-worker.md`
  - Generates Playwright test candidates from one evidenced UI flow.
  - Produces test candidates, selector review needs, and test data needs.

#### Recommended use

Run these after one bounded UI flow and the linked backend endpoint have been mapped:

```text
1. React stack UI mapper
2. UI/API contract mapper
3. Bounded backend flow mapper
4. Validator worker
5. Adversarial reviewer
6. Playwright from UI flow worker
```

#### Rule

Do not generate UI tests from guesses. Generate them from route, form, action, state, API client, endpoint, or flow evidence.

## From `docs/KIRO_CHANGELOG_2026_06_06_NGK_TRACE.md`

## Kiro Changelog — 2026-06-06 ngk Trace and Fractional Layers

### Summary

CodeAtlas V2 now includes explicit fractional-layer architecture for:

```text
Layer 1.5 — Data payload and DSL reconstruction
Layer 3.5 — Ecosystem and third-party bindings
Layer 5.5 — Explicit error and exception flows
```

These layers reduce AI hallucination by capturing OpenSearch payloads, third-party semantic roles, and error paths before full flow and rule derivation.

### Added / updated

- Updated `docs/FRAMEWORK_ARCHITECTURE_V2.md` with fractional layers and optional local knowledge databases.
- Updated `docs/LAYER_BUILD_CONTRACT.md` with fractional-layer acceptance criteria.
- Added `atlas/config/ecosystem-bindings.yaml` for ngk, React Router, TanStack Query, Leaflet, ReGraph, Material UI, and OpenSearch.
- Added `docs/NGK_TRACE_VISUAL_FLOW_EXPLORER.md`.
- Added `docs/NGK_ECOSYSTEM_HARDENING_PLAN.md`.
- Added `atlas/tools/ngk_trace_regraph_exporter.py`.

### New command blueprint

```bash
python3 atlas/tools/ngk_trace_regraph_exporter.py "POST /claims"
```

The exporter reads graph, flow, payload, error, and testing artifacts and emits:

```text
atlas/visualizer/ngk-trace/<trace-id>.regraph.json
atlas/visualizer/ngk-trace/<trace-id>.summary.md
```

### Next implementation tasks

1. Build a ts-morph TypeScript indexer for React Router, TanStack Query, Leaflet, ReGraph, API clients, and error states.
2. Build a Python import resolver for FastAPI dependencies and router inclusion tracing.
3. Build OpenSearch Query DSL reconstruction for query builder functions.
4. Build explicit Python/React error-flow extraction.
5. Compile `atlas/knowledge` into SQLite first, then optionally DuckDB or Kuzu.
