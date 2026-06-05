# Kiro Changelog

This changelog is written for Kiro, future AI agents, and humans maintaining CodeAtlas.

## 2026-06-05 — V2 deterministic framework foundation

### Summary

CodeAtlas now has a V2 architecture and first deterministic tool suite. The framework direction is now compiler-like: source snapshot → deterministic indexes → graph/flow seeds → validation/drift reports → visualizer exports → AI enrichment only where useful.

This update deliberately uses readable Python source. Do not reintroduce encoded/base64 payload launchers; Kiro and humans must be able to inspect and modify framework tools directly.

### Added docs

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

### Added tools

- `atlas/tools/codeatlas_v2_suite.py`
  - Plain Python deterministic foundation suite.
  - Provides `init`, `snapshot`, `index`, `graph`, `validate`, `drift-check`, `visualizer-export`, and `all` commands.
  - Produces source snapshots, file hashes, file/symbol/endpoint/route/API-client/test indexes, graph seeds, API-flow seeds, validation reports, drift reports, and visualizer JSON.

- `atlas/scripts/run-framework-v2-suite.sh`
  - Simple runner for the V2 suite.

### Added framework prompts

- `atlas/prompts/framework/00-discovery-planner.md`
- `atlas/prompts/framework/02-layer-implementation-worker.md`
- `atlas/prompts/framework/04-validator-worker.md`
- `atlas/prompts/framework/05-adversarial-reviewer.md`
- `atlas/prompts/framework/07-ui-ux-worker.md`
- `atlas/prompts/framework/08-test-archaeology-worker.md`

### Important behaviour changes

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

### Recommended next tasks

1. Refactor `codeatlas_v2_suite.py` into smaller modules under `atlas/tools/`.
2. Add stronger Python AST extraction for Pydantic schemas, FastAPI dependencies, middleware, and exception handlers.
3. Add stronger TypeScript/React extraction using a real TypeScript parser when available.
4. Add branch-aware API request flow generation.
5. Add UI state/interaction flow generation.
6. Add OpenSearch/config extractor.
7. Add fixture/mock/test archaeology extraction.
8. Add richer visualizer exporter and then build the visualizer UI.

## 2026-06-05 — Knowledge context, reverse verification, and MR review framework

### Summary

CodeAtlas now has a stronger post-extraction workflow for turning generated maps/rules/requirements into a normalized machine-readable knowledge layer, verifying generated claims back against code, refreshing Kiro context, and preparing safe GitLab merge-request reviews.

### Added

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

### Updated agents

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

### Important behaviour changes

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

### Recommended next command in an existing workspace

After pulling these framework changes into a workspace that already has generated Atlas artifacts:

```bash
bash atlas/scripts/run-post-extraction-suite.sh
```

This should:

1. normalize generated outputs into `atlas/knowledge/`,
2. reverse-check generated claims against code evidence,
3. refresh Kiro context packs and `.kiro/steering` files.

### Note about executable bits

Files created through GitHub's contents API may not retain executable permissions. If running scripts with `./atlas/scripts/...` fails, run:

```bash
chmod +x atlas/scripts/*.sh
```

or invoke scripts with `bash atlas/scripts/<script>.sh`.
