# Start Here for Kiro

You are reading CodeAtlas, a framework for turning mature application code into a reusable YAML knowledge foundation.

The user wants CodeAtlas to support:

- visualising the codebase
- deriving technical rules, business rules, user stories, epics, and high-level requirements
- creating automated Playwright tests
- creating API tests
- generating sample data
- creating compact Kiro context packs for developers
- debugging and feature-development assistance
- code health analysis and refactor planning
- PR impact analysis
- release branch governance
- ongoing rule maintenance across `develop/*`, `release/*`, and production branches

## Most important design principle

Do not treat requirements extraction as the first foundation.

The foundation is the semantic YAML Code Map.

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
→ Downstream tools
```

## What to read first

Read these files before making changes:

```text
README.md
docs/CODE_MAP_FOUNDATION.md
docs/YAML_CONTRACT.md
docs/TOOLING_ROADMAP.md
docs/MAINTENANCE_STRATEGY.md
docs/WORKFLOW.md
atlas/config/extraction-policy.md
```

## One-command first run

After the user edits `atlas/config/project.yaml` to point at their frontend/backend repos, the preferred command is:

```bash
export KIRO_AGENT="your-opus-agent-name"
export KIRO_DEFAULT_ARGS="--no-interactive --trust-all-tools"

./atlas/scripts/run-auto.sh
```

For a safer first pass:

```bash
./atlas/scripts/run-pilot-auto.sh
```

For map foundation only:

```bash
./atlas/scripts/run-architecture-discovery.sh
./atlas/scripts/run-global.sh
./atlas/scripts/run-code-map.sh
```

## Key output layers

```text
atlas/architecture-discovery/   architecture discovery and traversal guide
atlas/global/                   repo health, inventories, domain map
atlas/map/                      semantic YAML Code Map foundation
atlas/facts/                    technical facts derived from map
atlas/domains/                  technical/business rules, stories, review packs
atlas/code-health/              architecture and maintainability analysis
atlas/test-planning/            Playwright/API test planning
atlas/visualizer/               graph-ready visualisation data
atlas/sample-data/              fixture and seed data planning
atlas/context-packs/            compact Kiro/dev context packs
atlas/maintenance/              PR impact and rule delta outputs
atlas/releases/                 release baselines and release impact reports
atlas/audit/                    framework and YAML foundation audit
```

## What not to do

Do not:

- regenerate everything unnecessarily on every PR
- treat frontend-only validation as authoritative business enforcement
- treat backend-only endpoints as dead without evidence
- invent requirements unsupported by map/fact/code evidence
- build downstream tools by rescanning raw code when the YAML map already has the needed data
- overwrite reviewed rules without preserving IDs and review state

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
```

Runner scripts:

```bash
./atlas/scripts/run-tool-planner.sh
./atlas/scripts/run-code-health.sh
./atlas/scripts/run-test-planner.sh
./atlas/scripts/run-pr-impact.sh
./atlas/scripts/run-release-governance.sh
./atlas/scripts/run-context-pack.sh
./atlas/scripts/run-visualizer-planner.sh
./atlas/scripts/run-sample-data-planner.sh
./atlas/scripts/run-framework-audit.sh
./atlas/scripts/run-downstream-suite.sh
```

## Quality bar

The framework is only good enough when:

- map nodes have stable IDs
- major backend flows are mapped router → service → helper/service → data-access/OpenSearch
- frontend flows are mapped route → page → component → hook/state → API client → backend endpoint
- validation, permission, error, and state maps are populated
- technical facts derive from map evidence
- rules derive from facts or code references
- business rules do not appear magically from intuition
- downstream tools can consume YAML without needing to rescan the full codebase
- maintenance strategy supports multiple branches and releases
