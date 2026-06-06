# Workflow

## Philosophy

CodeAtlas is architecture-first, map-first, and knowledge-layer-first for downstream AI/tooling.

Do not start by extracting business rules.

First teach Kiro how the system is structured, then build a granular semantic YAML Code Map. Rules, stories, health checks, MR/PR impact reports, Playwright plans, sample-data plans, Kiro context packs, review guidance, and release reports should derive from that map and the normalized `atlas/knowledge/` layer.

The recommended progression is:

```text
Architecture Discovery
→ Architecture Verification
→ Repo Health Check
→ Repository Census
→ Domain Map
→ Granular Code Map
→ Technical Facts
→ Technical Rules
→ Business Rules
→ User Stories
→ Epics / High-Level Requirements
→ Knowledge Normalization
→ Reverse Verification
→ Kiro Context Refresh
→ Downstream Tools / MR Reviews
→ Ongoing Maintenance
```

## Recommended first run

```bash
export KIRO_AGENT="your-opus-agent-name"
export KIRO_DEFAULT_ARGS="--no-interactive --trust-all-tools"

bash atlas/scripts/run-foundation.sh
```

This runs:

1. architecture discovery / verification
2. repo health check
3. repository census
4. domain map
5. Code Map extraction
6. technical fact extraction

Review:

```text
atlas/architecture-discovery/human-review-checklist.md
atlas/architecture-discovery/extraction-traversal-guide.md
atlas/map/
atlas/facts/technical-facts.yaml
```

Then run a pilot extraction:

```bash
bash atlas/scripts/run-pilot-auto.sh
```

Review the pilot domain output before scaling.

## Full extraction

```bash
bash atlas/scripts/run-auto.sh
```

This should perform:

1. architecture discovery
2. architecture verification
3. repo health check
4. repository census
5. domain map
6. Code Map extraction
7. technical fact extraction
8. pilot domain extraction
9. validation
10. remaining domains

## Post-extraction accuracy and context suite

If the framework has already generated maps, rules, and requirements, do not immediately rerun from the beginning.

Run:

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

It creates or refreshes:

```text
atlas/knowledge/
atlas/knowledge/audit/
atlas/context-packs/
.kiro/steering/
```

Review:

```text
atlas/knowledge/audit/evidence-chain-audit.md
atlas/knowledge/audit/reverse-verification-report.md
atlas/knowledge/audit/unsupported-claims.md
atlas/knowledge/audit/targeted-rerun-plan.md
atlas/context-packs/context-refresh-report.md
```

## Quality gate

Before scaling to all domains or building downstream tools, inspect:

- architecture verification documents
- extraction traversal guide
- `atlas/map/*.yaml`
- `atlas/facts/technical-facts.yaml`
- technical rules
- business rules
- code references
- contract mappings
- contradictions
- review notes
- `atlas/knowledge/manifest.yaml`
- `atlas/knowledge/edges.yaml`
- `atlas/knowledge/indexes/*.yaml`
- reverse-verification findings
- unsupported claims

The output is only considered good if:

- the Code Map is semantic, not a raw AST dump
- important flows are mapped router → service → helper/service → OS/data-access
- frontend flows are mapped route → page → component → hook/state → API client → backend endpoint
- technical facts are traceable to map evidence
- requirements are traceable to technical facts and code references
- frontend/backend behaviour is distinguished correctly
- contradictions are surfaced
- architecture assumptions are evidenced
- generated claims can be reverse-checked against source evidence
- low-confidence or stale claims are marked `needs_review: true`
- `atlas/knowledge` exports nodes, edges, indexes, graph data, and UI cards

## Code Map review checklist

When reviewing `atlas/map/`, check:

- Are major domains present?
- Are backend endpoints mapped to service functions?
- Are service functions mapped to helper/data-access/OpenSearch calls?
- Are Pydantic schemas/models mapped to endpoints?
- Are frontend API clients mapped to backend endpoints?
- Are validation rules split between frontend and backend?
- Are permission checks split between frontend and backend?
- Are error conditions captured?
- Are state transitions captured where workflows exist?
- Are low-confidence areas marked `needs_review: true`?

## Knowledge layer review checklist

When reviewing `atlas/knowledge/`, check:

- Are nodes exported by artifact type?
- Are edges exported separately?
- Are stable IDs preserved?
- Are business rules linked to technical rules?
- Are technical rules linked to facts/evidence?
- Are user stories linked to business rules?
- Are acceptance criteria linked to rules or stories?
- Are graph exports valid JSON?
- Are UI cards usable without parsing Markdown?
- Are unsupported claims listed?
- Are stale maps/rules identified by reverse verification?

## Downstream tools

After `atlas/map/`, `atlas/facts/`, domain artifacts, and preferably `atlas/knowledge/` exist, run:

```bash
bash atlas/scripts/run-downstream-suite.sh
```

Or run individual tools:

```bash
bash atlas/scripts/run-framework-audit.sh
bash atlas/scripts/run-code-health.sh
bash atlas/scripts/run-visualizer-planner.sh
bash atlas/scripts/run-test-planner.sh
bash atlas/scripts/run-sample-data-planner.sh
bash atlas/scripts/run-context-pack.sh
bash atlas/scripts/run-project-agent-builder.sh
```

These create:

```text
atlas/audit/
atlas/code-health/
atlas/visualizer/
atlas/test-planning/
atlas/sample-data/
atlas/context-packs/
atlas/agents/
```

## GitLab merge-request review

Draft-only review:

```bash
bash atlas/scripts/run-mr-review.sh <mr_iid>
```

The default mode generates review artifacts only and must not post comments.

Approved posting mode:

```bash
export CODEATLAS_REVIEW_MODE=approved-post
export CODEATLAS_POST_REVIEW_COMMENTS=true
export CODEATLAS_REVIEW_APPROVED=true
bash atlas/scripts/run-mr-review.sh <mr_iid>
```

Every AI-generated MR comment must start with:

```text
✦ AI GENERATED REVIEW
```

Prefer inline comments when a finding is tied to a changed line or hunk. If exact inline positioning is uncertain, generate a draft only and require human verification.

## Maintenance lifecycle

After the initial extraction, CodeAtlas becomes a living baseline.

Recommended ongoing flow:

```text
Merge Request / Pull Request
→ Changed files
→ Impacted knowledge/map nodes
→ Impacted domains/rules
→ Targeted extraction if needed
→ Knowledge normalization
→ Reverse verification
→ Rule delta
→ Contradiction scan
→ Draft MR/PR review
→ Human approval for meaningful requirement changes
→ Baseline update
```

Maintenance commands:

```bash
bash atlas/scripts/run-pr-impact.sh
bash atlas/scripts/run-release-governance.sh
bash atlas/scripts/run-knowledge-normalizer.sh
bash atlas/scripts/run-reverse-verification.sh
bash atlas/scripts/run-context-refresh.sh
bash atlas/scripts/run-mr-review.sh <mr_iid>
```

See:

```text
docs/MAINTENANCE_STRATEGY.md
docs/KNOWLEDGE_CONTEXT_LAYER.md
docs/CODE_ATLAS_REVERSE_VERIFICATION.md
docs/MERGE_REQUEST_REVIEW_FRAMEWORK.md
docs/KIRO_CONTEXT_USAGE.md
docs/YAML_CONTRACT.md
docs/ROADMAP_AND_IMPLEMENTATION_PLAN.md
```
