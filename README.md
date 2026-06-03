# CodeAtlas

CodeAtlas is a Kiro-powered architecture discovery, requirements extraction, and requirements maintenance framework for mature codebases.

It is designed for decoupled applications such as:

- React / TypeScript frontend
- FastAPI / Pydantic backend
- layered backend architecture with routers, service files, helper/service dependencies, and OpenSearch/data-access modules

CodeAtlas reverse-engineers the system bottom-up into a traceable requirements pyramid:

```text
Code References
→ Technical Rules
→ Business Rules
→ User Stories
→ Epics
→ High-Level Requirements
```

It also maintains a living requirements baseline as development continues across `develop/*`, `release/*`, and production branches.

## Why CodeAtlas exists

Mature systems often contain their real requirements inside the codebase rather than in a requirements document.

CodeAtlas turns embedded behaviour into a structured, reviewable, traceable corpus that can later power an interactive source-of-truth UI.

The long-term goal is bidirectional traceability:

```text
High-Level Requirement
→ Epic
→ User Story
→ Business Rule
→ Technical Rule
→ Code Reference
```

and backwards:

```text
Code Reference
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
| Code references | Provide evidence back to file/symbol/line ranges |
| Technical rules | Capture objective code behaviour |
| Contract mappings | Link frontend API calls to backend endpoints/models |
| Business rules | Translate implementation facts into business language |
| User stories | Express behaviour from an actor/user perspective |
| Epics and high-level requirements | Group behaviours into product-level capabilities |
| Contradictions and dead-code candidates | Detect mismatches, regressions, unused paths, and structural problems |
| `.kiro/steering` updates | Give future Kiro sessions durable architecture/debugging context |
| Maintenance reports | Keep rules aligned as code changes over time |

## Agent names

CodeAtlas uses short, purpose-specific Kiro agents:

| Agent | Purpose |
|---|---|
| `atlas-cartographer` | global repo discovery, architecture discovery, domain mapping |
| `domain-scout` | bounded domain extraction |
| `rift-hunter` | contradiction, mismatch, and dead-code review |
| `memory-smith` | `.kiro/steering` updates |

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

Run architecture discovery first. This lets Kiro do the heavy groundwork of deriving backend/frontend architecture before it extracts requirements.

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

This runs:

1. architecture discovery
2. architecture verification
3. repo health check
4. repository census
5. domain map
6. auto-selected pilot domain
7. validation
8. all remaining domains

## Maintenance strategy

CodeAtlas should not be a one-time documentation dump. It should become a living requirements baseline.

For ongoing development:

```text
Code change
→ impacted files
→ impacted domains
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

Recommended future modes:

```bash
codeatlas pr-impact --base develop --head feature/foo
codeatlas rule-delta --domain knowledge_management
codeatlas release-freeze --release 2026.07
codeatlas drift-check --branch develop
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
  domains/
  releases/
  logs/

.kiro/
  agents/
  steering/
```

`atlas/` contains detailed extraction artifacts.

`.kiro/steering/` contains compact durable memory for future Kiro debugging, feature work, refactoring, and onboarding.
