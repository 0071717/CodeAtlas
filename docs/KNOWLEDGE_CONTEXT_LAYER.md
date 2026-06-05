# CodeAtlas Knowledge Context Layer

The `atlas/knowledge/` layer is the normalized, machine-readable source of truth above generated maps, facts, rules, stories, and requirements.

It exists so Kiro, other AI agents, merge-request reviewers, validation tools, and future UIs do not need to scrape scattered Markdown/YAML outputs or rescan the whole codebase for every question.

## Purpose

`atlas/knowledge/` should make generated CodeAtlas output:

- easy for AI agents to use as context
- easy for machines to diff and validate
- easy for future UIs to render
- easy to trace from requirement back to code evidence
- easy to update with targeted reruns

## Input layers

The knowledge layer is generated from existing CodeAtlas outputs:

```text
atlas/architecture-discovery/
atlas/global/
atlas/map/
atlas/facts/
atlas/domains/
atlas/audit/
atlas/context-packs/
.kiro/steering/
```

Agents should inspect raw source code only when:

1. a generated node has missing evidence,
2. reverse verification needs to validate a claim,
3. a map node is stale or contradictory,
4. the user explicitly asks for implementation work, or
5. the generated context is insufficient for the question.

## Output structure

```text
atlas/knowledge/
  manifest.yaml
  nodes/
    domains.yaml
    code_refs.yaml
    code_map_nodes.yaml
    technical_facts.yaml
    technical_rules.yaml
    business_rules.yaml
    user_stories.yaml
    acceptance_criteria.yaml
    epics.yaml
    high_level_requirements.yaml
    contradictions.yaml
    dead_code_candidates.yaml
  edges.yaml
  indexes/
    by_domain.yaml
    by_file.yaml
    by_code_ref.yaml
    by_requirement.yaml
    by_business_rule.yaml
    by_user_story.yaml
  graph/
    requirements-graph.json
    cytoscape-elements.json
    force-graph.json
    mermaid-summary.mmd
  cards/
    business-rule-cards.json
    user-story-cards.json
    requirement-cards.json
    domain-cards.json
  audit/
    evidence-chain-audit.md
    reverse-verification-report.md
    orphan-node-report.md
    unsupported-claims.md
    confidence-report.md
    contradiction-report.md
```

## Canonical node shape

Every normalized node should follow this shape where applicable:

```yaml
id: br.claims.approval.requires_manager_permission
type: business_rule
domain: claims
name: Claims approval requires manager permission
summary: Users can only approve claims when they have manager-level permission.
statement: Users may only approve claims if they have the required manager approval permission.
status: candidate
confidence: high
needs_review: false
source_artifacts:
  - atlas/domains/claims/business-rules.yaml
derived_from:
  - tr.claims.approval.backend_requires_manager_permission
evidence:
  - type: technical_rule
    id: tr.claims.approval.backend_requires_manager_permission
  - type: code_ref
    id: code.backend.claims_router.approve_claim
enforcement:
  frontend: partial
  backend: true
  data_access: false
ui:
  label: Manager permission required for claim approval
  group: claims
  importance: high
ai:
  update_policy: Preserve this ID unless the underlying business meaning changes.
  context_priority: high
  review_guidance: If permission logic changes, update the technical rule and evidence chain first.
```

## Required common fields

All nodes should include:

```text
id
type
name
summary
confidence
needs_review
status
evidence
source_artifacts
```

Where applicable, nodes should also include:

```text
domain
statement
description
derived_from
enforcement
acceptance_criteria
related_nodes
ui
ai
```

## Stable IDs

Prefer stable hierarchical IDs:

```text
domain.<domain>
code.<repo>.<domain>.<symbol>
fact.<domain>.<meaning>
tr.<domain>.<meaning>
br.<domain>.<meaning>
us.<domain>.<meaning>
ac.<domain>.<story>.<criterion>
epic.<domain>.<meaning>
hlr.<domain>.<meaning>
contradiction.<domain>.<meaning>
```

Do not base IDs only on line numbers.

## Canonical edge shape

Relationships must be exported separately in `atlas/knowledge/edges.yaml`:

```yaml
edges:
  - id: edge.br.claims.approval.requires_manager_permission.derived_from.tr.claims.approval.backend_requires_manager_permission
    source: br.claims.approval.requires_manager_permission
    target: tr.claims.approval.backend_requires_manager_permission
    type: DERIVED_FROM
    confidence: high
    needs_review: false
    evidence:
      - type: technical_rule
        id: tr.claims.approval.backend_requires_manager_permission
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
IMPLEMENTS
HAS_ACCEPTANCE_CRITERION
BELONGS_TO_DOMAIN
CONTRADICTS
TESTS
IMPACTED_BY
REVERSE_VERIFIED_BY
NEEDS_REVIEW_BECAUSE
```

## AI context priority

When Kiro or another agent answers code questions, it should prefer context in this order:

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

## Code ↔ Atlas reverse verification

Accuracy must be checked in both directions:

```text
code → generated Atlas artifacts
Atlas artifacts → code evidence
```

Reverse verification asks: "Do the generated maps, facts, rules, stories, and requirements still match the code they claim to describe?"

It should produce:

```text
atlas/knowledge/audit/reverse-verification-report.md
atlas/knowledge/audit/stale-map-candidates.yaml
atlas/knowledge/audit/invalid-evidence.yaml
atlas/knowledge/audit/claim-to-code-checks.yaml
```

Reverse verification should check:

- referenced files still exist
- referenced symbols still exist where possible
- line ranges still contain the expected behaviour where possible
- business rules still derive from technical rules
- technical rules still derive from facts or code/map evidence
- frontend/backend contract claims still match API clients, endpoints, schemas, and errors
- permissions, validation, errors, state transitions, and side effects are not invented
- stale or unsupported claims are marked `needs_review: true`

## Machine/UI contract

The future UI should treat these files as primary inputs:

```text
atlas/knowledge/graph/requirements-graph.json
atlas/knowledge/graph/cytoscape-elements.json
atlas/knowledge/cards/*.json
atlas/knowledge/indexes/*.yaml
```

The UI should not parse random Markdown as the source of truth. Markdown reports are for humans. YAML/JSON nodes, edges, indexes, and cards are the machine contract.

## Update policy

When generated artifacts change:

1. rerun only impacted CodeAtlas layers where possible,
2. rerun the knowledge normalizer,
3. rerun reverse verification,
4. refresh context packs and steering files,
5. review unsupported claims and low-confidence nodes,
6. approve or reject baseline changes.

Do not overwrite reviewed IDs or review states without preserving history.
