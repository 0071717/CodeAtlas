# Workflow

## Philosophy

CodeAtlas is architecture-first and map-first.

Do not start by extracting business rules.

First teach Kiro how the system is structured, then build a granular semantic YAML Code Map. Rules, stories, health checks, PR impact reports, and release reports should derive from that map.

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
→ Ongoing Maintenance
```

## Recommended first run

```bash
export KIRO_AGENT="your-opus-agent-name"
export KIRO_DEFAULT_ARGS="--no-interactive --trust-all-tools"

./atlas/scripts/run-architecture-discovery.sh
```

Review:

```text
atlas/architecture-discovery/human-review-checklist.md
atlas/architecture-discovery/extraction-traversal-guide.md
```

Then build the semantic map foundation:

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

Review the pilot domain output before scaling.

## Full extraction

```bash
./atlas/scripts/run-auto.sh
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

## Quality gate

Before scaling to all domains, inspect:

- architecture verification documents
- extraction traversal guide
- `atlas/map/*.yaml`
- `atlas/facts/technical-facts.yaml`
- technical rules
- code references
- contract mappings
- contradictions
- review notes

The output is only considered good if:

- the Code Map is semantic, not a raw AST dump
- important flows are mapped router → service → helper/service → OS/data-access
- frontend flows are mapped route → page → component → hook/state → API client → backend endpoint
- technical facts are traceable to map evidence
- requirements are traceable to technical facts and code references
- frontend/backend behaviour is distinguished correctly
- contradictions are surfaced
- architecture assumptions are evidenced

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

## Maintenance lifecycle

After the initial extraction, CodeAtlas becomes a living baseline.

Recommended ongoing flow:

```text
Pull Request
→ Changed files
→ Impacted Code Map nodes
→ Impacted domains/rules
→ Targeted extraction
→ Rule delta
→ Contradiction scan
→ Review
→ Baseline update
```

See:

```text
docs/MAINTENANCE_STRATEGY.md
docs/CODE_MAP_FOUNDATION.md
```
