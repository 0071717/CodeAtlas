# CodeAtlas Roadmap and Implementation Plan

Canonical forward plan for implementation, transfer readiness, and follow-up work.

This file preserves the relevant content from retired standalone files so the repo has fewer stale entrypoints without losing historical context.

## From `docs/NEXT_STEPS_FOR_KIRO.md`

## Next Steps for Kiro

Use this after pulling the latest CodeAtlas framework changes into an Amazon Workspace or other local workspace that already has generated Atlas artifacts.

### Situation

The full Atlas framework may already have been run, and local Kiro/Claude work may have modified CodeAtlas prompts, scripts, and generated outputs.

Do **not** rerun the entire framework from the beginning yet.

Instead:

```text
1. preserve the current generated outputs
2. normalize them into atlas/knowledge
3. reverse-check generated claims against code evidence
4. refresh Kiro context packs and steering files
5. inspect unsupported claims and targeted rerun recommendations
6. rerun only weak layers/domains
```

### First command

From the CodeAtlas repo root:

```bash
chmod +x atlas/scripts/*.sh 2>/dev/null || true
bash atlas/scripts/run-post-extraction-suite.sh
```

This runs:

```text
atlas/scripts/run-knowledge-normalizer.sh
atlas/scripts/run-reverse-verification.sh
atlas/scripts/run-context-refresh.sh
```

### Review outputs

After the suite, inspect:

```text
atlas/knowledge/README.md
atlas/knowledge/manifest.yaml
atlas/knowledge/audit/evidence-chain-audit.md
atlas/knowledge/audit/reverse-verification-report.md
atlas/knowledge/audit/unsupported-claims.md
atlas/knowledge/audit/confidence-report.md
atlas/knowledge/audit/targeted-rerun-plan.md
atlas/context-packs/context-refresh-report.md
.kiro/steering/codeatlas-context.md
.kiro/steering/codeatlas-rules.md
.kiro/steering/codeatlas-review-guidance.md
.kiro/steering/codeatlas-debugging-guidance.md
```

### Copy-paste prompt for Kiro

```text
You are working in my local CodeAtlas workspace.

Context:
I have already run the full Atlas framework once and generated maps, facts, technical rules, business rules, user stories, epics, high-level requirements, audits, and context outputs. Kiro/Claude may also have modified the framework locally.

Do not rerun the full framework from the beginning yet.

Goal:
Make the existing generated Atlas artifacts accurate, machine-readable, and useful for future Kiro code answers, debugging, feature work, tests, merge-request reviews, and a future UI.

Read first:
- docs/CHANGELOG.md
- docs/ROADMAP_AND_IMPLEMENTATION_PLAN.md
- docs/KNOWLEDGE_CONTEXT_LAYER.md
- docs/CODE_ATLAS_REVERSE_VERIFICATION.md
- docs/KIRO_CONTEXT_USAGE.md
- docs/MERGE_REQUEST_REVIEW_FRAMEWORK.md
- docs/YAML_CONTRACT.md
- docs/CODE_MAP_FOUNDATION.md
- atlas/config/extraction-policy.md

Then run:

bash atlas/scripts/run-post-extraction-suite.sh

After it completes, review:
- atlas/knowledge/audit/evidence-chain-audit.md
- atlas/knowledge/audit/reverse-verification-report.md
- atlas/knowledge/audit/unsupported-claims.md
- atlas/knowledge/audit/targeted-rerun-plan.md
- atlas/context-packs/context-refresh-report.md

Rules:
1. Treat current generated Atlas outputs as a baseline candidate, not approved truth.
2. Normalize current outputs into atlas/knowledge.
3. Reverse-check generated claims against source-code evidence.
4. If source code conflicts with generated Atlas context, trust source code and mark the generated node stale or needs_review.
5. Do not invent requirements or missing evidence.
6. Preserve stable IDs, confidence, needs_review, and review state.
7. Prefer targeted reruns over full framework reruns.
8. Refresh context packs and .kiro/steering so future Kiro sessions use atlas/knowledge first.
9. Do not post merge-request comments unless I explicitly approve.
10. Any AI-generated MR comment must start with: ✦ AI GENERATED REVIEW

Deliverables:
- atlas/knowledge/* normalized outputs
- atlas/knowledge/audit/* verification reports
- refreshed atlas/context-packs/*
- refreshed .kiro/steering/*
- a short summary of what is reliable, what is weak, and what should be rerun next
```

### Decision tree after the suite

| Finding | Action |
|---|---|
| Knowledge layer missing or malformed | rerun `run-knowledge-normalizer.sh` |
| Many unsupported claims | rerun reverse verification, then targeted domain extraction |
| Map nodes stale or wrong | rerun map/facts for impacted domain |
| Weak business rules | rerun business-rule derivation from technical rules |
| Weak stories/epics/HLRs | rerun story/epic/HLR derivation only |
| Frontend/backend contract drift | rerun API/schema/contract mapping and contradiction scan |
| Architecture discovery wrong globally | then rerun architecture discovery and foundation |

### Merge-request review command

Draft-only review:

```bash
bash atlas/scripts/run-mr-review.sh <mr_iid>
```

Approved posting mode, only after human review:

```bash
export CODEATLAS_REVIEW_MODE=approved-post
export CODEATLAS_POST_REVIEW_COMMENTS=true
export CODEATLAS_REVIEW_APPROVED=true
bash atlas/scripts/run-mr-review.sh <mr_iid>
```

Default mode must not post comments.

### Source of truth for future UI

The future UI should consume:

```text
atlas/knowledge/graph/requirements-graph.json
atlas/knowledge/graph/cytoscape-elements.json
atlas/knowledge/cards/*.json
atlas/knowledge/indexes/*.yaml
```

The UI should not parse random Markdown as its source of truth.

## From `docs/TOOLING_ROADMAP.md`

## CodeAtlas Tooling Roadmap

CodeAtlas YAML is intended to be a reusable foundation, not a single-purpose extraction output.

The core foundation is:

```text
atlas/map/*.yaml
atlas/facts/technical-facts.yaml
atlas/domains/*/*.yaml
```

Downstream tools should read these artifacts rather than repeatedly scanning raw source code.

### Tool categories

| Tool | Inputs | Outputs | Purpose |
|---|---|---|---|
| Code visualizer | `atlas/map` | graph/UI data | Explore routes, endpoints, services, UI flows, rules |
| PR impact analyzer | changed files + `atlas/map` | PR impact report | Identify affected domains, rules, tests, UI screens |
| Code health analyzer | `atlas/map` + facts | health scores, violations | Improve architecture and consistency |
| Contract checker | `api-map`, `schema-map`, `validation-map` | mismatches | Detect frontend/backend drift |
| Playwright generator | `ui-flow-map`, `api-map`, stories | test specs | Generate user-flow E2E tests |
| API test generator | `backend-map`, `schema-map`, facts | API tests | Generate endpoint tests from contracts/rules |
| Test gap analyzer | facts/rules + test evidence | coverage gaps | Find important behaviour without tests |
| Sample data generator | schemas + state map + stories | seed fixtures | Create realistic test/dev data |
| Debug navigator | map + facts + errors | debugging paths | Show likely files/functions for a bug |
| Refactor planner | call graph + health | refactor tickets | Safely improve messy areas |
| Release impact reporter | baseline + branch delta | release report | Explain behaviour changes by release |
| Kiro context packer | selected domain map | `.md` context pack | Give dev agents compact project context |
| Project Kiro agent builder | context packs + YAML | generated agent configs | Create debugger/feature/test/refactor agents for developers |

### Build order

Recommended order:

1. Framework audit
2. Code Map visualizer data exporter
3. PR impact analyzer
4. Contract checker
5. Code health analyzer
6. Test gap analyzer
7. Playwright test generator
8. Sample data generator
9. Kiro context packer
10. Project-specific Kiro agent builder
11. Release governance tools
12. Interactive web UI

### Tool design principles

- Read YAML artifacts first.
- Do not rescan raw code unless the map is missing information.
- Prefer deterministic parsing and graph traversal before LLM reasoning.
- Keep outputs reviewable and diffable.
- Preserve stable IDs.
- Avoid overwriting approved rules without marking them superseded.
- Separate advisory findings from blocking findings.
- Treat generated tool outputs as plans unless explicitly asked to modify app repos.

### Custom Kiro agent

Use `.kiro/agents/atlas-forge.json` for tool building.

Typical command:

```bash
export KIRO_AGENT="atlas-forge"
export KIRO_DEFAULT_ARGS="--no-interactive --trust-all-tools"
./atlas/scripts/run-tool-planner.sh
```

You can also override with your Opus agent:

```bash
export KIRO_AGENT="your-opus-agent-name"
./atlas/scripts/run-tool-planner.sh
```

### Tool runners

```bash
./atlas/scripts/run-framework-audit.sh
./atlas/scripts/run-code-health.sh
./atlas/scripts/run-visualizer-planner.sh
./atlas/scripts/run-test-planner.sh
./atlas/scripts/run-sample-data-planner.sh
./atlas/scripts/run-context-pack.sh
./atlas/scripts/run-project-agent-builder.sh
./atlas/scripts/run-pr-impact.sh
./atlas/scripts/run-release-governance.sh
```

Run the main downstream suite:

```bash
./atlas/scripts/run-downstream-suite.sh
```

### Project-specific agents

After CodeAtlas has generated `atlas/context-packs/`, run:

```bash
./atlas/scripts/run-project-agent-builder.sh
```

This produces proposed agents under:

```text
atlas/agents/generated-agents/
```

Expected generated agent types:

- `project-debugger`
- `project-feature-builder`
- `project-test-generator`
- `project-refactor-planner`
- `project-rule-maintainer`
- `project-sample-data-builder`
- `project-code-reviewer`

These agents should use compact context packs and YAML references rather than embedding large YAML dumps in prompts.

## From `docs/IMPLEMENTATION_TICKETS_PRE_TRANSFER.md`

## Pre-Transfer Implementation Tickets

These are the remaining high-value tickets that should be executed by Kiro/Codex after the repo is transferred or in the final pre-transfer window. Each ticket is intentionally bounded.

### CA-V2-001 — Promote canonical V2 path everywhere

Objective: Ensure Kiro always starts with the deterministic V2 path.

Files:

```text
README.md
docs/START_HERE_FOR_KIRO.md
docs/CANONICAL_EXECUTION_PATH.md
docs/LEGACY_AND_EXPERIMENTAL_PATHS.md
atlas/scripts/run-framework-v2-suite.sh
```

Done when:

```text
No first-run guide recommends run-auto.sh as default.
V2 canonical wrapper is the documented first command.
Legacy scripts are documented as exploratory only.
```

### CA-V2-002 — Finish JSON artifact migration

Objective: Make `.json` canonical and `.yaml` fallback only.

Files:

```text
atlas/tools/codeatlas_v2_canonical.py
atlas/tools/codeatlas_v2_suite.py
atlas/tools/ngk_trace_regraph_exporter.py
docs/TOOL_SUITE_V2.md
```

Steps:

```text
1. Ensure V2 canonical runner writes/promotes JSON artifacts.
2. Update readers to prefer .json and fall back to .yaml.
3. Add validation warning for legacy .yaml files.
4. Keep backwards compatibility until all tools are migrated.
```

Validation:

```bash
python3 atlas/tools/codeatlas_v2_canonical.py all
python3 atlas/tools/codeatlas_v2_canonical.py validate
```

### CA-V2-003 — Build FastAPI materialisation extractor

Objective: Resolve FastAPI app/router/include_router/dependencies into materialised endpoint records.

Create:

```text
atlas/tools/backend/extract_fastapi_materialized.py
atlas/index/router-index.json
atlas/index/materialized-endpoint-index.json
atlas/runtime/dependency-map.json
atlas/runtime/router-inclusion-map.json
```

Acceptance:

```text
APIRouter prefixes are applied.
include_router chains are represented.
Depends(...) references are linked to symbols where possible.
Router-level and endpoint-level dependencies are distinguished.
```

### CA-V2-004 — Build TypeScript AST frontend extractor

Objective: Replace regex as canonical frontend extraction.

Create:

```text
atlas/tools/frontend/package.json
atlas/tools/frontend/src/extract-routes.ts
atlas/tools/frontend/src/extract-tanstack-query.ts
atlas/tools/frontend/src/extract-api-clients.ts
atlas/tools/frontend/src/extract-ui-actions.ts
atlas/tools/frontend/src/extract-leaflet-regraph.ts
```

Recommended parser:

```text
ts-morph first
tree-sitter optional for fast broad scanning
```

Acceptance:

```text
React Router route objects and JSX routes are captured.
TanStack query/mutation hooks include queryKey/mutationFn/queryFn where static.
Leaflet/ReGraph components are captured as semantic UI nodes.
API client calls are normalized.
```

### CA-V2-005 — Build OpenSearch Query DSL extractor

Objective: Implement Layer 1.5 payload/DSL reconstruction.

Create:

```text
atlas/tools/backend/extract_opensearch_payloads.py
atlas/payloads/opensearch-query-dsl.json
atlas/payloads/generated-query-builders.json
atlas/graph/payload-graph.json
```

Acceptance:

```text
Literal query dicts are captured.
search/msearch body=... calls are linked to owner symbols.
Dynamic unresolved variables are listed, not invented.
OpenSearch nodes can show Query DSL in ngk trace.
```

### CA-V2-006 — Build explicit error-flow extractor

Objective: Implement Layer 5.5 error/exception flows.

Create:

```text
atlas/tools/build_error_flows.py
atlas/errors/python-exception-map.json
atlas/errors/frontend-error-map.json
atlas/errors/error-boundary-map.json
atlas/flows/error-flows.json
atlas/graph/error-flow-graph.json
```

Acceptance:

```text
Python raise/try/except sites are represented.
HTTPException status codes are captured where static.
React catch/ErrorBoundary/TanStack error states are represented.
ngk trace can display error branches.
```

### CA-V2-007 — Build test archaeology mapper

Objective: Link existing tests to endpoints/routes/services/flows.

Create:

```text
atlas/tools/testing/map_test_coverage.py
atlas/testing/test-inventory.json
atlas/testing/fixture-map.json
atlas/testing/mock-map.json
atlas/testing/coverage-links.json
atlas/testing/coverage-gaps.json
```

Acceptance:

```text
FastAPI TestClient calls are linked to endpoint IDs.
pytest fixtures are mapped.
Mocks are classified.
Weak vs partial vs strong coverage is represented.
ngk trace can color nodes by coverage.
```

### CA-V2-008 — Build SQLite read model

Objective: Compile canonical file artifacts into a fast local read model for ngk.

Create:

```text
atlas/db/schema.sql
atlas/db/load_sqlite.py
atlas/knowledge/atlas.sqlite
```

Acceptance:

```text
nodes, edges, files, flows, payloads, errors, tests, evidence are queryable.
ngk can query SQLite before falling back to raw files.
YAML/JSON remains canonical; SQLite is derived.
```

### CA-V2-009 — Replace ngk trace BFS with trace bundles

Objective: Make ngk trace render deterministic trace bundles rather than free graph neighbourhoods.

Create:

```text
atlas/tools/build_trace_bundles.py
atlas/traces/trace-bundles.json
atlas/visualizer/ngk-trace/*.regraph.json
```

Acceptance:

```text
Trace starts from materialized endpoint or UI route ID.
Common path, branches, errors, payloads, and tests are explicit.
Missing links appear as findings, not invisible omissions.
```

### CA-V2-010 — Add prompt-safety and artifact redaction

Objective: Prevent secrets/PII/config leakage through prompts and generated knowledge.

Create:

```text
atlas/tools/security/redact_artifacts.py
atlas/audit/redaction-report.json
atlas/config/redaction-policy.yaml
```

Acceptance:

```text
.env and secret-like values are never sent to AI prompts.
Sensitive payloads can be hashed or redacted.
Artifacts are classified as prompt-safe or restricted.
```
