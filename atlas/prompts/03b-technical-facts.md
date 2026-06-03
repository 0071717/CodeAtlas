You are acting as a technical fact extraction agent.

Goal:
Derive normalized technical facts from the semantic Code Map YAML.

Technical facts are evidence-backed observations of what the code does. They sit between the granular map and technical rules.

Do not create business rules yet.
Do not create user stories yet.

Read:
- docs/YAML_CONTRACT.md
- docs/CODE_MAP_FOUNDATION.md
- atlas/config/schemas/technical-fact.schema.json
- atlas/map/*.yaml
- atlas/global/domain-map.yaml
- atlas/config/extraction-policy.md

Write:
- atlas/facts/technical-facts.yaml

Also write per-domain fact files when useful:
- atlas/domains/<domain_id>/technical-facts.yaml

Technical fact example:

```yaml
technical_facts:
  - id: fact.knowledge.search.requires_query
    domain: knowledge
    source_type: validation
    statement: KnowledgeSearchRequest.query is required by the backend.
    derived_from:
      - validation.backend.knowledge.search_query_required
    evidence:
      - type: map_node
        id: validation.backend.knowledge.search_query_required
    confidence: high
    needs_review: false
    review_status: unreviewed

  - id: fact.knowledge.search.filters_by_set_access
    domain: knowledge
    source_type: service_condition
    statement: search_knowledge restricts search results to sets accessible by the user.
    derived_from:
      - service.knowledge.search_knowledge
      - os.knowledge.search_documents
    evidence:
      - type: map_node
        id: service.knowledge.search_knowledge
      - type: map_node
        id: os.knowledge.search_documents
    confidence: high
    needs_review: false
    review_status: unreviewed
```

Extract facts for:
- endpoint behaviour
- request/response contracts
- validation rules
- permission checks
- service-layer conditions
- data-access/OpenSearch query behaviour
- state transitions
- error conditions
- side effects
- frontend UI states
- frontend validation
- frontend/backend contract links
- test evidence where available

Rules:
1. Every fact must trace to map evidence.
2. Prefer small precise facts over broad vague facts.
3. Use confidence high only when directly evidenced by map/code evidence.
4. If the evidence is incomplete, use medium or low confidence and mark `needs_review: true`.
5. Do not infer business intent yet.
6. Do not collapse multiple behaviours into one fact if they can change independently.
7. Preserve stable IDs if rerunning.
8. Use `review_status: unreviewed` for newly generated facts.
9. Do not mark facts as accepted unless explicit review evidence exists.
