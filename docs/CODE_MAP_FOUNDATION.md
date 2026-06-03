# Code Map Foundation

CodeAtlas should treat the YAML map as the canonical intermediate representation of the application.

The long-term flow should be:

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
→ High-level requirements
```

The YAML map is not just documentation. It is a reusable semantic model of the codebase that other tools can consume.

## Why add a granular map layer?

The original extraction artifacts are useful, but business rules become more reliable when they are derived from a structured code map rather than repeatedly inferred directly from raw source code.

A granular map makes it easier to build:

- business rule derivation
- PR impact analysis
- release impact reports
- frontend/backend contract checks
- architecture conformance checks
- code health scoring
- test gap analysis
- debugging navigators
- refactor planners
- interactive source-of-truth UIs

## Semantic map, not AST dump

The map should not capture every variable, import, JSX element, or line of code.

It should capture behaviourally meaningful structure:

- domains
- routes
- endpoints
- schemas/models
- API clients
- service functions
- helper functions
- data-access/OpenSearch calls
- call edges
- validations
- permissions
- state transitions
- errors
- side effects
- frontend/backend contract links
- tests/evidence where available

## Recommended map layout

```text
atlas/
  map/
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

  facts/
    technical-facts.yaml
```

## Backend map focus

For a layered FastAPI backend, map the request lifecycle:

```text
router endpoint
→ request model
→ auth/permission dependency
→ service function
→ helper/service calls
→ OS/OpenSearch/data-access layer
→ response model
→ errors/side effects
```

Example:

```yaml
backend_map:
  endpoints:
    - id: endpoint.knowledge.search
      domain: knowledge
      method: POST
      path: /knowledge/search
      router_file: app/routers/knowledge_router.py
      handler: search_knowledge
      request_model: KnowledgeSearchRequest
      response_model: KnowledgeSearchResponse
      auth_dependencies:
        - get_current_user
        - require_set_access
      calls:
        - target: service.knowledge.search_knowledge
          call_type: router_to_service
      errors:
        - status_code: 403
          condition: user lacks set access
        - status_code: 422
          condition: invalid request payload
```

## Service map focus

Service functions are usually where business behaviour lives.

```yaml
services:
  - id: service.knowledge.search_knowledge
    file: app/services/knowledge_service.py
    function: search_knowledge
    domain: knowledge
    called_by:
      - endpoint.knowledge.search
    calls:
      - service.sets.get_accessible_sets
      - os.knowledge.search_documents
    responsibilities:
      - validates user access
      - builds search filters
      - excludes archived records
      - formats search results
    conditions:
      - if set_id is provided, restrict results to that set
      - if include_archived is false, exclude archived records
    side_effects: []
```

## Data-access / OpenSearch map focus

Files such as `*_os.py` should be treated as a data-access/search layer.

```yaml
data_access:
  - id: os.knowledge.search_documents
    file: app/os/knowledge_os.py
    function: search_documents
    backend: opensearch
    index_names:
      - knowledge_index
    query_behaviour:
      filters:
        - set_id
        - archived
        - user_access
      ranking:
        - text relevance
        - recency boost
    called_by:
      - service.knowledge.search_knowledge
```

## Frontend map focus

Map user-facing flows:

```text
route
→ page
→ component
→ hook/state
→ API client
→ backend endpoint
```

Example:

```yaml
frontend_map:
  routes:
    - id: route.knowledge.search
      path: /knowledge/search
      page_file: src/pages/knowledge/SearchPage.tsx
      components:
        - component.knowledge.SearchPanel
        - component.knowledge.SearchResults
      hooks:
        - hook.knowledge.useKnowledgeSearch
      api_calls:
        - api.knowledge.searchKnowledge

  api_clients:
    - id: api.knowledge.searchKnowledge
      file: src/api/knowledgeApi.ts
      function: searchKnowledge
      method: POST
      path: /knowledge/search
      request_type: KnowledgeSearchRequest
      response_type: KnowledgeSearchResponse
      maps_to_backend_endpoint: endpoint.knowledge.search
```

## Validation map

```yaml
validation_map:
  frontend:
    - id: validation.frontend.knowledge.search_query_required
      field: query
      rule: required
      location: src/features/knowledge/searchSchema.ts
      applies_to:
        - api.knowledge.searchKnowledge

  backend:
    - id: validation.backend.knowledge.search_query_required
      model: KnowledgeSearchRequest
      field: query
      rule: required
      location: app/schemas/knowledge.py
      applies_to:
        - endpoint.knowledge.search
```

## Permission map

```yaml
permission_map:
  backend:
    - id: permission.backend.knowledge.search.requires_set_access
      endpoint: endpoint.knowledge.search
      dependency: require_set_access
      rule: user must have access to requested set

  frontend:
    - id: permission.frontend.knowledge.search.visible_to_authenticated_user
      route: route.knowledge.search
      rule: user must be authenticated
```

## Technical facts

Technical facts sit between the code map and technical rules.

They are normalized, evidence-backed statements of observable behaviour.

```yaml
technical_facts:
  - id: fact.knowledge.search.requires_query
    domain: knowledge
    source_type: validation
    statement: KnowledgeSearchRequest.query is required by the backend.
    evidence:
      - code_ref.backend.schema.knowledge_search_request.query
    confidence: high

  - id: fact.knowledge.search.filters_by_set_access
    domain: knowledge
    source_type: service_condition
    statement: search_knowledge restricts search results to sets accessible by the user.
    evidence:
      - code_ref.backend.service.knowledge.search_knowledge
      - code_ref.backend.os.knowledge.search_documents
    confidence: high
```

Technical rules should derive from facts rather than raw code where possible.

## Business rule derivation

Instead of asking Kiro to infer business rules directly from source code, the preferred flow is:

```text
code map
→ technical facts
→ technical rules
→ business rules
```

This makes rules easier to review, diff, maintain, and reuse.
