# CodeAtlas YAML Contract

The CodeAtlas YAML files are the foundation layer for downstream tools.

They should be treated as a stable semantic contract, not disposable generated notes.

## Design goals

The YAML contract should support:

- code visualisation
- requirements derivation
- technical/business rule maintenance
- PR impact analysis
- release governance
- Playwright/API test planning
- sample data planning
- custom Kiro/Codex context packs
- code health analysis
- refactor planning

## Stable ID convention

Use stable, hierarchical IDs where possible.

Recommended patterns:

```text
repo.<repo_id>
domain.<domain_id>
route.<domain>.<name>
component.<domain>.<name>
hook.<domain>.<name>
api.<domain>.<function>
endpoint.<domain>.<operation>
schema.<domain>.<model>
service.<domain>.<function>
helper.<domain>.<function>
os.<domain>.<function>
validation.<layer>.<domain>.<name>
permission.<layer>.<domain>.<name>
error.<domain>.<name>
state.<domain>.<entity>.<state_or_transition>
fact.<domain>.<name>
tr.<domain>.<name>
br.<domain>.<name>
us.<domain>.<name>
epic.<domain>.<name>
hlr.<domain>.<name>
contradiction.<domain>.<name>
```

Avoid IDs based only on line numbers because line numbers change frequently.

## Required common fields

Most map/fact/rule items should include:

```yaml
id: endpoint.knowledge.search
domain: knowledge
name: Search knowledge
kind: backend_endpoint
confidence: high
needs_review: false
evidence:
  - repo: backend
    file: app/routers/knowledge_router.py
    symbol: search_knowledge
    line_start: 42
    line_end: 70
```

## Confidence values

Use only:

```text
high
medium
low
```

## Review field

Use:

```yaml
needs_review: true
```

when a claim is plausible but not fully proven.

## Evidence standard

Evidence should point back to code, map nodes, or facts.

Code evidence:

```yaml
evidence:
  - type: code
    repo: backend
    file: app/services/knowledge_service.py
    symbol: search_knowledge
    line_start: 80
    line_end: 125
```

Map evidence:

```yaml
evidence:
  - type: map_node
    id: service.knowledge.search_knowledge
```

Fact evidence:

```yaml
evidence:
  - type: technical_fact
    id: fact.knowledge.search.filters_by_set_access
```

## Edge convention

When exporting graph-ready relationships, prefer this shape:

```yaml
edges:
  - id: edge.endpoint.knowledge.search.calls.service.knowledge.search_knowledge
    source: endpoint.knowledge.search
    target: service.knowledge.search_knowledge
    type: CALLS
    confidence: high
    evidence:
      - type: code
        file: app/routers/knowledge_router.py
        symbol: search_knowledge
```

Recommended edge types:

```text
OWNS
CONTAINS
CALLS
MAPS_TO
VALIDATES
REQUIRES_PERMISSION
RETURNS
RAISES_ERROR
DERIVED_FROM
EVIDENCED_BY
AFFECTS
CONTRADICTS
TESTS
```

## Technical fact convention

```yaml
technical_facts:
  - id: fact.knowledge.search.requires_set_access
    domain: knowledge
    source_type: permission
    statement: Knowledge search requires the user to have access to the requested set.
    derived_from:
      - permission.backend.knowledge.search.requires_set_access
      - service.knowledge.search_knowledge
    evidence:
      - type: map_node
        id: permission.backend.knowledge.search.requires_set_access
    confidence: high
    needs_review: false
```

## Rule derivation convention

```yaml
technical_rules:
  - id: tr.knowledge.search.requires_set_access
    domain: knowledge
    statement: The backend restricts knowledge search to sets the user can access.
    derived_from_facts:
      - fact.knowledge.search.requires_set_access
    evidence:
      - type: technical_fact
        id: fact.knowledge.search.requires_set_access
    confidence: high
    needs_review: false
```

## Business rule derivation convention

```yaml
business_rules:
  - id: br.knowledge.search.access_limited_to_allowed_sets
    domain: knowledge
    statement: Users may only search knowledge within sets they are permitted to access.
    derived_from_technical_rules:
      - tr.knowledge.search.requires_set_access
    enforcement:
      frontend: partial
      backend: true
      data_access: true
    confidence: high
    needs_review: false
```

## Tooling rule

Downstream tools should prefer the YAML contract over raw source code.

Only inspect raw code when:

- a map node is missing evidence
- a tool needs line-level details not present in YAML
- the map is stale or inconsistent
- a validation/audit prompt explicitly asks for verification
