# CodeAtlas

CodeAtlas is a Kiro-powered architecture and requirements discovery framework for mature codebases.

It reverse-engineers a decoupled React/TypeScript frontend and FastAPI/Pydantic backend into a traceable requirements pyramid:

```text
Code References
→ Technical Rules
→ Business Rules
→ User Stories
→ Epics
→ High-Level Requirements
```

It also discovers architecture first, so Kiro understands how to traverse your app before extracting requirements.

## Why CodeAtlas exists

Mature systems often contain the real requirements inside the codebase rather than in a requirements document.

CodeAtlas turns those embedded behaviours into a structured, reviewable, traceable corpus that can later power an interactive source-of-truth UI.

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

## Workspace layout

Recommended:

```text
workspace/
  codeatlas/
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

## Run architecture discovery first

```bash
export KIRO_AGENT="your-opus-agent-name"
export KIRO_DEFAULT_ARGS="--no-interactive --trust-all-tools"

./atlas/scripts/run-architecture-discovery.sh
```

Review:

```text
atlas/architecture-discovery/human-review-checklist.md
```

## Run a pilot extraction

```bash
./atlas/scripts/run-pilot-auto.sh
```

## Run fully hands-off

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

## Outputs

```text
atlas/
  architecture-discovery/
  config/
  prompts/
  scripts/
  global/
  domains/
  logs/

.kiro/
  agents/
  steering/
```

`atlas/` contains the detailed extraction artifacts.

`.kiro/steering/` contains compact durable memory for future Kiro debugging, feature work, refactoring, and onboarding.
