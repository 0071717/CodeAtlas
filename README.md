# CodeAtlas

CodeAtlas is a Kiro-powered architecture discovery, semantic code mapping, requirements extraction, and requirements maintenance framework for mature codebases.

It is designed for decoupled applications such as:

- React / TypeScript frontend
- FastAPI / Pydantic backend
- layered backend architecture with routers, service files, helper/service dependencies, and OpenSearch/data-access modules

CodeAtlas no longer treats requirements extraction as the first foundation layer. The preferred foundation is now a granular YAML **Code Map**:

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

The Code Map is a semantic, reusable model of the application. Business rules, PR impact analysis, code health checks, test-gap reports, refactor plans, release governance, Playwright planning, sample data, and visualisers can all derive from it.

## Start here

For Kiro/dev agents, read:

```text
docs/START_HERE_FOR_KIRO.md
```

For the YAML contract, read:

```text
docs/YAML_CONTRACT.md
```

For downstream tools, read:

```text
docs/TOOLING_ROADMAP.md
```

## Why CodeAtlas exists

Mature systems often contain their real requirements inside the codebase rather than in a requirements document.

CodeAtlas turns embedded behaviour into structured YAML artifacts that are reviewable, traceable, and reusable by other tools.

The long-term goal is bidirectional traceability:

```text
High-Level Requirement
→ Epic
→ User Story
→ Business Rule
→ Technical Rule
→ Technical Fact
→ Code Map Node
→ Code Reference
```

and backwards:

```text
Code Reference
→ Code Map Node
→ Technical Fact
→ Technical Rule
→ Business Rule
→ User Story
→ Epic
→ High-Level Requirement
```

## What CodeAtlas produces

| Output | Why it exists |
|---|---|
| Architecture discovery docs | Teach Kiro how the frontend/backend are structured before extraction |
| Repo health report | Detect frameworks, layout, generated folders, and context-bloat risks |
| Frontend/backend inventories | Catalogue routes, endpoints, schemas, services, hooks, forms, API clients |
| Domain map | Slice the system into manageable business domains |
| **Granular Code Map YAML** | Build the reusable semantic model of the codebase |
| Technical facts | Normalize objective, evidence-backed behaviour from the map |
| Code references | Provide evidence back to file/symbol/line ranges |
| Technical rules | Capture objective system behaviour derived from technical facts |
| Contract mappings | Link frontend API calls to backend endpoints/models |
| Business rules | Translate technical rules into business language |
| User stories | Express behaviour from an actor/user perspective |
| Epics and high-level requirements | Group behaviours into product-level capabilities |
| Contradictions and dead-code candidates | Detect mismatches, regressions, unused paths, and structural problems |
| `.kiro/steering` updates | Give future Kiro sessions durable architecture/debugging context |
| Maintenance reports | Keep rules aligned as code changes over time |
| Downstream tool artifacts | Visualisers, code health reports, Playwright plans, sample data, context packs |

## Code Map foundation

The Code Map should be semantic, not a raw AST dump.

It should capture:

- domains
- UI routes
- backend endpoints
- frontend API clients
- Pydantic schemas/models
- service functions
- helper/service calls
- OpenSearch/data-access calls such as `*_os.py`
- call graph edges
- validation rules
- permission checks
- error conditions
- state transitions
- side effects
- frontend/backend contract links
- test evidence where available

Recommended map outputs:

```text
atlas/map/
  repo-map.yaml
  domain-map.yaml
  code-references.yaml
  backend-map.yaml
  frontend-map.yaml
  api-map.yaml
  schema-map.yaml
  call-graph.yaml
  ui-flow-map.yaml
  data-access-map.yaml
  validation-map.yaml
  permission-map.yaml
  error-map.yaml
  state-map.yaml
  integration-map.yaml

atlas/facts/
  technical-facts.yaml
```

See:

```text
docs/CODE_MAP_FOUNDATION.md
docs/YAML_CONTRACT.md
```

## Agent names

CodeAtlas uses short, purpose-specific Kiro agents:

| Agent | Purpose |
|---|---|
| `atlas-cartographer` | architecture discovery, repo discovery, domain mapping, Code Map extraction |
| `domain-scout` | bounded domain extraction |
| `rift-hunter` | contradiction, mismatch, and dead-code review |
| `memory-smith` | `.kiro/steering` updates |
| `atlas-forge` | builds downstream tools from the YAML foundation |

You can override all of them with your own Opus 4.6 agent:

```bash
export KIRO_AGENT="your-opus-agent-name"
```

Recommended headless mode:

```bash
export KIRO_DEFAULT_ARGS="--no-interactive --trust-all-tools"
```

## Workspace layout

Recommended:

```text
workspace/
  CodeAtlas/
  frontend-repo/
  backend-repo/
```

Edit:

```text
atlas/config/project.yaml
```

Set:

```yaml
repositories:
  frontend:
    path: ../frontend-repo

  backend:
    path: ../backend-repo
```

## Recommended first run

Run architecture discovery first. This lets Kiro do the heavy groundwork of deriving backend/frontend architecture before it maps the codebase.

```bash
export KIRO_AGENT="your-opus-agent-name"
export KIRO_DEFAULT_ARGS="--no-interactive --trust-all-tools"

./atlas/scripts/run-architecture-discovery.sh
```

Review and edit:

```text
atlas/architecture-discovery/human-review-checklist.md
atlas/architecture-discovery/backend-architecture-verified.md
atlas/architecture-discovery/frontend-architecture-verified.md
atlas/architecture-discovery/extraction-traversal-guide.md
```

Then build the granular Code Map and technical facts:

```bash
./atlas/scripts/run-code-map.sh
```

Review:

```text
atlas/map/
atlas/facts/technical-facts.yaml
```

Then run a pilot extraction:

```bash
./atlas/scripts/run-pilot-auto.sh
```

Review:

```text
atlas/domains/<pilot_domain>/12-review-notes.md
```

Then run fully hands-off:

```bash
./atlas/scripts/run-auto.sh
```

This should run:

1. architecture discovery
2. architecture verification
3. repo health check
4. repository census
5. domain map
6. Code Map extraction
7. technical fact extraction
8. auto-selected pilot domain
9. validation
10. all remaining domains

## Downstream tooling

After `atlas/map/`, `atlas/facts/`, and domain artifacts exist, run:

```bash
./atlas/scripts/run-framework-audit.sh
./atlas/scripts/run-code-health.sh
./atlas/scripts/run-visualizer-planner.sh
./atlas/scripts/run-test-planner.sh
./atlas/scripts/run-sample-data-planner.sh
./atlas/scripts/run-context-pack.sh
```

Or run the suite:

```bash
./atlas/scripts/run-downstream-suite.sh
```

Outputs:

```text
atlas/audit/
atlas/code-health/
atlas/visualizer/
atlas/test-planning/
atlas/sample-data/
atlas/context-packs/
```

## Maintenance strategy

CodeAtlas should not be a one-time documentation dump. It should become a living requirements and code-quality baseline.

For ongoing development:

```text
Code change
→ impacted files
→ impacted Code Map nodes
→ impacted domains/rules
→ targeted re-extraction
→ rule delta
→ contradiction/regression scan
→ PR/release report
→ human approval for meaningful requirement changes
→ baseline update
```

See:

```text
docs/MAINTENANCE_STRATEGY.md
```

Maintenance runners:

```bash
./atlas/scripts/run-pr-impact.sh
./atlas/scripts/run-release-governance.sh
```

Recommended future CLI modes:

```bash
codeatlas pr-impact --base develop --head feature/foo
codeatlas rule-delta --domain knowledge_management
codeatlas release-freeze --release 2026.07
codeatlas drift-check --branch develop
codeatlas architecture-conformance --domain knowledge_management
codeatlas test-gap-analysis --domain knowledge_management
```

## Branch policy

| Branch type | CodeAtlas behaviour |
|---|---|
| `develop/*` | advisory checks plus moderate blocking for serious issues |
| `release/*` | strict checks against frozen release baseline |
| `main` / production | strictest check against approved release baseline |

## Outputs

```text
atlas/
  architecture-discovery/
  config/
  prompts/
  scripts/
  global/
  map/
  facts/
  domains/
  code-health/
  visualizer/
  test-planning/
  sample-data/
  context-packs/
  maintenance/
  releases/
  audit/
  logs/

.kiro/
  agents/
  steering/
```

`atlas/map/` and `atlas/facts/` contain the reusable foundation artifacts.

`atlas/domains/` contains domain-level rule/story/requirement artifacts.

`.kiro/steering/` contains compact durable memory for future Kiro debugging, feature work, refactoring, and onboarding.
