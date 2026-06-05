# Start Here for Kiro

You are reading CodeAtlas, a framework for turning mature application code into a reusable YAML and knowledge-graph foundation.

The user wants CodeAtlas to support:

- visualising the codebase
- deriving technical rules, business rules, user stories, epics, and high-level requirements
- reverse-checking generated maps/rules/requirements against source code
- creating automated Playwright tests
- creating API tests
- generating sample data
- creating compact Kiro context packs for developers
- debugging and feature-development assistance
- code health analysis and refactor planning
- GitLab merge-request review with safe draft-first AI comments
- PR/MR impact analysis
- release branch governance
- ongoing rule maintenance across `develop/*`, `release/*`, and production branches

## Most important design principle

Do not treat requirements extraction as the first foundation.

The foundation is:

```text
semantic Code Map → technical facts → rules/requirements → normalized knowledge layer → reverse verification → context packs / UI / reviews
```

Preferred flow:

```text
Raw code
→ Architecture discovery
→ Repo inventory
→ Granular Code Map YAML
→ Technical facts
→ Technical rules
→ Business rules
→ User stories
→ Epics
→ High-Level Requirements
→ Normalized Knowledge Layer
→ Reverse verification
→ Kiro context / downstream tools / MR reviews
```

## What to read first

Read these files before making changes:

```text
README.md
docs/NEXT_STEPS_FOR_KIRO.md
docs/KIRO_CHANGELOG.md
docs/KIRO_CONTEXT_USAGE.md
docs/KNOWLEDGE_CONTEXT_LAYER.md
docs/CODE_ATLAS_REVERSE_VERIFICATION.md
docs/MERGE_REQUEST_REVIEW_FRAMEWORK.md
docs/CODE_MAP_FOUNDATION.md
docs/YAML_CONTRACT.md
docs/TOOLING_ROADMAP.md
docs/MAINTENANCE_STRATEGY.md
docs/WORKFLOW.md
atlas/config/extraction-policy.md
```

## If the full framework has already been run

Do **not** rerun everything from the beginning by default.

First run the post-extraction suite:

```bash
chmod +x atlas/scripts/*.sh 2>/dev/null || true
bash atlas/scripts/run-post-extraction-suite.sh
```

This runs:

```text
run-knowledge-normalizer.sh
run-reverse-verification.sh
run-context-refresh.sh
```

Then review:

```text
atlas/knowledge/audit/evidence-chain-audit.md
atlas/knowledge/audit/reverse-verification-report.md
atlas/knowledge/audit/unsupported-claims.md
atlas/knowledge/audit/targeted-rerun-plan.md
atlas/context-packs/context-refresh-report.md
.kiro/steering/
```

Only after that, decide whether a targeted rerun is needed.

## One-command first run for a new project

After the user edits `atlas/config/project.yaml` to point at their frontend/backend repos, the preferred command is:

```bash
export KIRO_AGENT="your-opus-agent-name"
export KIRO_DEFAULT_ARGS="--no-interactive --trust-all-tools"

bash atlas/scripts/run-auto.sh
bash atlas/scripts/run-post-extraction-suite.sh
```

For a safer first pass:

```bash
bash atlas/scripts/run-pilot-auto.sh
bash atlas/scripts/run-post-extraction-suite.sh
```

For map foundation only:

```bash
bash atlas/scripts/run-architecture-discovery.sh
bash atlas/scripts/run-global.sh
bash atlas/scripts/run-code-map.sh
```

## Key output layers

```text
atlas/architecture-discovery/   architecture discovery and traversal guide
atlas/global/                   repo health, inventories, domain map
atlas/map/                      semantic YAML Code Map foundation
atlas/facts/                    technical facts derived from map
atlas/domains/                  technical/business rules, stories, review packs
atlas/knowledge/                normalized nodes, edges, indexes, graph exports, cards, audits
atlas/code-health/              architecture and maintainability analysis
atlas/test-planning/            Playwright/API test planning
atlas/visualizer/               graph-ready visualisation data
atlas/sample-data/              fixture and seed data planning
atlas/context-packs/            compact Kiro/dev context packs
atlas/reviews/                  GitLab MR review packs
atlas/maintenance/              PR/MR impact and rule delta outputs
atlas/releases/                 release baselines and release impact reports
atlas/audit/                    framework and YAML foundation audit
.kiro/steering/                 compact durable Kiro memory
```

## Context priority for code answers

When answering a code question, debugging, planning feature work, generating tests, or reviewing an MR, prefer this order:

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

If generated Atlas context conflicts with source code, trust source code and mark the generated Atlas artifact stale or unsupported.

## What not to do

Do not:

- regenerate everything unnecessarily on every PR/MR
- treat generated rules as infallible when reverse verification is weak
- treat frontend-only validation as authoritative business enforcement
- treat backend-only endpoints as dead without evidence
- invent requirements unsupported by map/fact/code evidence
- build downstream tools by rescanning raw code when `atlas/knowledge` already has the needed data
- overwrite reviewed rules without preserving IDs and review state
- post MR review comments without explicit approval

## What to do when building tools

Use `atlas-forge` or the user's Opus agent.

Tool prompts live in:

```text
atlas/prompts/20-build-tool-from-map.md
atlas/prompts/21-code-health-analysis.md
atlas/prompts/22-playwright-test-planner.md
atlas/prompts/23-pr-impact-analysis.md
atlas/prompts/24-release-governance.md
atlas/prompts/25-kiro-context-pack.md
atlas/prompts/26-visualizer-data-planner.md
atlas/prompts/27-sample-data-planner.md
atlas/prompts/28-framework-audit.md
atlas/prompts/29-project-agent-builder.md
atlas/prompts/30-knowledge-normalizer.md
atlas/prompts/31-reverse-verification.md
atlas/prompts/32-kiro-context-refresh.md
atlas/prompts/33-merge-request-review.md
```

Runner scripts:

```bash
bash atlas/scripts/run-tool-planner.sh
bash atlas/scripts/run-code-health.sh
bash atlas/scripts/run-test-planner.sh
bash atlas/scripts/run-pr-impact.sh
bash atlas/scripts/run-release-governance.sh
bash atlas/scripts/run-context-pack.sh
bash atlas/scripts/run-visualizer-planner.sh
bash atlas/scripts/run-sample-data-planner.sh
bash atlas/scripts/run-framework-audit.sh
bash atlas/scripts/run-knowledge-normalizer.sh
bash atlas/scripts/run-reverse-verification.sh
bash atlas/scripts/run-context-refresh.sh
bash atlas/scripts/run-post-extraction-suite.sh
bash atlas/scripts/run-mr-review.sh <mr_iid>
bash atlas/scripts/run-downstream-suite.sh
```

## Merge-request review safety

Default MR review mode is draft-only:

```bash
bash atlas/scripts/run-mr-review.sh <mr_iid>
```

Only post comments when all approval flags are true:

```bash
export CODEATLAS_REVIEW_MODE=approved-post
export CODEATLAS_POST_REVIEW_COMMENTS=true
export CODEATLAS_REVIEW_APPROVED=true
bash atlas/scripts/run-mr-review.sh <mr_iid>
```

Every AI-generated comment must begin with:

```text
✦ AI GENERATED REVIEW
```

Prefer inline comments when a finding is tied to a changed line or hunk.

## Quality bar

The framework is only good enough when:

- map nodes have stable IDs
- major backend flows are mapped router → service → helper/service → data-access/OpenSearch
- frontend flows are mapped route → page → component → hook/state → API client → backend endpoint
- validation, permission, error, and state maps are populated
- technical facts derive from map evidence
- rules derive from facts or code references
- business rules do not appear magically from intuition
- `atlas/knowledge` can represent the generated outputs as nodes, edges, indexes, graph exports, and UI cards
- reverse verification checks generated claims back against source code
- unsupported/stale claims are marked `needs_review: true`
- downstream tools can consume `atlas/knowledge` without needing to rescan the full codebase
- maintenance strategy supports branches, releases, and MR reviews
