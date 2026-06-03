# Extraction Policy

## Core principle

Never reverse-engineer the whole application into requirements in one pass.

CodeAtlas is architecture-first, map-first, and then rule-driven.

Work in bounded phases and bounded domains.

## Preferred order

Always prefer this order:

1. Architecture Discovery
2. Architecture Verification
3. Repo Health Check
4. Repository Census
5. Domain Map
6. Granular Code Map YAML
7. Technical Facts
8. Technical Rules
9. Contract Mappings
10. Business Rules
11. User Stories
12. Epics
13. High-Level Requirements
14. Contradictions / Dead-Code Candidates
15. Review Pack
16. Kiro Steering Updates

## Map-first rule

Do not derive business rules directly from raw code where avoidable.

Prefer:

```text
Raw code
→ Semantic Code Map
→ Technical facts
→ Technical rules
→ Business rules
```

The Code Map is the reusable foundation for other tools such as PR impact analysis, code health checks, contract checking, release impact reports, test gap analysis, and refactor planning.

## Semantic map rules

The map should capture behaviourally meaningful structure, not every syntax detail.

Capture:

- domains
- UI routes
- backend endpoints
- request/response schemas
- frontend API clients
- service functions
- helper/service dependencies
- data-access/OpenSearch functions such as `*_os.py`
- call edges
- validation rules
- permission checks
- error conditions
- state transitions
- side effects
- frontend/backend contract links
- tests/evidence where available

Avoid dumping:

- every variable assignment
- every import unless architecturally relevant
- every JSX element
- generated/vendor/cache files
- raw AST structures that do not help behaviour analysis

## Backend traversal rule

For layered FastAPI backends, trace behaviour through the full call path:

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

Do not stop extraction at the router.

## Frontend traversal rule

For React/TypeScript frontends, trace behaviour through:

```text
route
→ page/layout
→ component
→ hook/state/form
→ API client
→ backend endpoint
→ loading/error/success UI behaviour
```

Do not treat an API client as the whole frontend behaviour.

## Evidence rules

- Every map item should include evidence where possible: repo, file, symbol, and line range.
- Every technical fact must derive from map evidence.
- Every technical rule must derive from one or more technical facts or code references.
- Every business rule must derive from one or more technical rules.
- Every user story must derive from one or more business rules.
- Every epic must derive from user stories.
- Every high-level requirement must derive from epics.
- Do not invent requirements unsupported by evidence.

## Frontend/backend authority

- Backend is authoritative for auth, permission enforcement, persistence, server validation, and side effects.
- Frontend is authoritative for visible UI behavior, navigation, local state, and form interaction.
- Frontend-only validation is not considered strong business enforcement unless backend agrees.

## Contradictions

Contradictions are first-class outputs. Do not hide them in notes.

Examples:

- Frontend sends a field the backend does not accept.
- Frontend marks a field optional but backend requires it.
- Frontend hides an admin action but backend does not enforce admin permission.
- Backend returns an error the frontend does not handle.
- State names differ between frontend and backend.
- Router bypasses service layer where architecture requires service delegation.
- Business logic is duplicated inconsistently across frontend and backend.

## Dead code

Backend endpoints not called by frontend are not automatically dead. Mark them as `backend_only_endpoint` unless route registration, tests, and references prove they are unused.

## Confidence

Use:

- `high` when directly evidenced by code or map evidence
- `medium` when inferred from structure/naming with supporting evidence
- `low` when uncertain or dependent on runtime/external usage

Use `needs_review: true` whenever a claim is plausible but not fully proven.
