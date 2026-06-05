# CodeAtlas

CodeAtlas is a Kiro-powered architecture discovery, semantic code mapping, requirements extraction, requirements maintenance, and review framework for mature codebases.

It is designed for decoupled applications such as:

- React / TypeScript frontend
- FastAPI / Pydantic backend
- layered backend architecture with routers, services, helper/service dependencies, and OpenSearch/data-access modules

## Core model

CodeAtlas is **architecture-first**, **map-first**, and now **knowledge-layer-first** for downstream AI/tooling.

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
→ Context packs / AI agents / UI / MR reviews
```

The Code Map is the semantic reusable model of the application. The normalized knowledge layer under `atlas/knowledge/` turns generated maps, facts, rules, stories, and requirements into machine-readable nodes, edges, indexes, graph exports, UI cards, and audit reports.

## Start here

For Kiro/dev agents, read:

```text
docs/START_HERE_FOR_KIRO.md
docs/NEXT_STEPS_FOR_KIRO.md
docs/KIRO_CONTEXT_USAGE.md
```

For the knowledge/context contract, read:

```text
docs/KNOWLEDGE_CONTEXT_LAYER.md
docs/CODE_ATLAS_REVERSE_VERIFICATION.md
docs/YAML_CONTRACT.md
```

For merge-request reviews, read:

```text
docs/MERGE_REQUEST_REVIEW_FRAMEWORK.md
```

## Why CodeAtlas exists

Mature systems often contain their real requirements inside the codebase rather than in a requirements document.

CodeAtlas turns embedded behaviour into structured artifacts that are reviewable, traceable, verifiable, and reusable by AI agents, humans, tests, reviewers, and future UIs.

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

Reverse verification adds another safety loop:

```text
Generated Atlas artifacts
→ check back against source code and evidence chains
→ stale/unsupported claims
→ targeted rerun plan
```

## What CodeAtlas produces

| Output | Why it exists |
|---|---|
| Architecture discovery docs | Teach Kiro how the frontend/backend are structured before extraction |
| Repo health report | Detect frameworks, layout, generated folders, and context-bloat risks |
| Frontend/backend inventories | Catalogue routes, endpoints, schemas, services, hooks, forms, API clients |
| Domain map | Slice the system into manageable business domains |
| Granular Code Map YAML | Build the reusable semantic model of the codebase |
| Technical facts | Normalize objective, evidence-backed behaviour from the map |
| Technical rules | Capture objective system behaviour derived from technical facts |
| Contract mappings | Link frontend API calls to backend endpoints/models |
| Business rules | Translate technical rules into business language |
| User stories | Express behaviour from an actor/user perspective |
| Epics and high-level requirements | Group behaviours into product-level capabilities |
| Contradictions and dead-code candidates | Detect mismatches, regressions, unused paths, and structural problems |
| `atlas/knowledge/` | Normalize generated outputs into nodes, edges, indexes, graph exports, UI cards, and audits |
| Reverse verification reports | Check generated maps/rules/requirements back against source evidence |
| Context packs and `.kiro/steering` | Give future Kiro sessions compact, accurate project context |
| MR review packs | Draft GitLab merge-request comments and rule/contract/test findings safely |
| Downstream tool artifacts | Visualisers, code health reports, Playwright plans, sample data, context packs |

## Code Map foundation

The Code Map should be semantic, not a raw AST dump. It should capture:

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

## Knowledge layer

After the framework generates maps/facts/domain artifacts, normalize them into:

```text
atlas/knowledge/
  manifest.yaml
  nodes/
  edges.yaml
  indexes/
  graph/
  cards/
  audit/
```

Future UIs and AI agents should consume:

```text
atlas/knowledge/graph/requirements-graph.json
atlas/knowledge/graph/cytoscape-elements.json
atlas/knowledge/cards/*.json
atlas/knowledge/indexes/*.yaml
```

Do not make the UI parse random Markdown as the source of truth.

## Agent names

CodeAtlas uses short, purpose-specific Kiro agents:

| Agent | Purpose |
|---|---|
| `atlas-cartographer` | architecture discovery, repo discovery, domain mapping, Code Map extraction, targeted map refreshes |
| `domain-scout` | bounded domain extraction and domain refreshes |
| `rift-hunter` | contradiction, mismatch, dead-code, unsupported-claim, and reverse-verification review |
| `memory-smith` | `.kiro/steering` and context-pack updates |
| `atlas-forge` | builds downstream tools from the knowledge/YAML foundation |

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

Run architecture discovery first:

```bash
export KIRO_AGENT="your-opus-agent-name"
export KIRO_DEFAULT_ARGS="--no-interactive --trust-all-tools"

bash atlas/scripts/run-architecture-discovery.sh
```

Then build the granular Code Map and technical facts:

```bash
bash atlas/scripts/run-code-map.sh
```

Then run a pilot extraction:

```bash
bash atlas/scripts/run-pilot-auto.sh
```

Then run fully hands-off if the pilot is good:

```bash
bash atlas/scripts/run-auto.sh
```

## After extraction

If the full framework has already been run, do **not** automatically rerun from the beginning. First run the post-extraction accuracy/context suite:

```bash
chmod +x atlas/scripts/*.sh 2>/dev/null || true
bash atlas/scripts/run-post-extraction-suite.sh
```

This runs:

1. `run-knowledge-normalizer.sh`
2. `run-reverse-verification.sh`
3. `run-context-refresh.sh`

Review:

```text
atlas/knowledge/audit/evidence-chain-audit.md
atlas/knowledge/audit/reverse-verification-report.md
atlas/knowledge/audit/unsupported-claims.md
atlas/knowledge/audit/targeted-rerun-plan.md
atlas/context-packs/context-refresh-report.md
.kiro/steering/
```

## Downstream tooling

After `atlas/map/`, `atlas/facts/`, domain artifacts, and preferably `atlas/knowledge/` exist, run:

```bash
bash atlas/scripts/run-framework-audit.sh
bash atlas/scripts/run-code-health.sh
bash atlas/scripts/run-visualizer-planner.sh
bash atlas/scripts/run-test-planner.sh
bash atlas/scripts/run-sample-data-planner.sh
bash atlas/scripts/run-context-pack.sh
```

Or run the suite:

```bash
bash atlas/scripts/run-downstream-suite.sh
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

## Merge-request reviews

Draft-only GitLab MR review:

```bash
bash atlas/scripts/run-mr-review.sh <mr_iid>
```

This should generate:

```text
atlas/reviews/mr-<iid>/review-summary.md
atlas/reviews/mr-<iid>/inline-comments-draft.md
atlas/reviews/mr-<iid>/general-comment-draft.md
atlas/reviews/mr-<iid>/glab-post-commands.sh
```

Default mode must not post comments.

Posting is allowed only when all approval flags are true:

```bash
export CODEATLAS_REVIEW_MODE=approved-post
export CODEATLAS_POST_REVIEW_COMMENTS=true
export CODEATLAS_REVIEW_APPROVED=true
bash atlas/scripts/run-mr-review.sh <mr_iid>
```

Every AI-generated comment must start with:

```text
✦ AI GENERATED REVIEW
```

## Maintenance strategy

CodeAtlas should not be a one-time documentation dump. It should become a living requirements and code-quality baseline.

For ongoing development:

```text
Code change
→ impacted files
→ impacted Code Map / knowledge nodes
→ impacted domains/rules
→ targeted re-extraction
→ knowledge normalization
→ reverse verification
→ rule delta
→ contradiction/regression scan
→ MR/release report
→ human approval for meaningful requirement changes
→ baseline update
```

See:

```text
docs/MAINTENANCE_STRATEGY.md
docs/KIRO_CHANGELOG.md
docs/NEXT_STEPS_FOR_KIRO.md
```

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
  knowledge/
  code-health/
  visualizer/
  test-planning/
  sample-data/
  context-packs/
  maintenance/
  releases/
  reviews/
  audit/
  logs/

.kiro/
  agents/
  steering/
```

`atlas/map/` and `atlas/facts/` contain the reusable foundation artifacts.

`atlas/domains/` contains domain-level rule/story/requirement artifacts.

`atlas/knowledge/` contains normalized machine-readable nodes, edges, indexes, graph exports, cards, and audits.

`.kiro/steering/` contains compact durable memory for future Kiro debugging, feature work, refactoring, testing, and reviews.
