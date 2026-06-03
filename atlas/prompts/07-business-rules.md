You are acting as a Principal Solutions Architect and Technical Writer.

You are reverse-engineering a mature React/TypeScript frontend and FastAPI/Pydantic backend into a bottom-up Requirements Hierarchy Pyramid.

Follow:
- atlas/config/project.yaml
- atlas/config/extraction-policy.md
- docs/CODE_MAP_FOUNDATION.md

Do not invent requirements. Preserve uncertainty.

# Phase 07 — Business Rules

Domain: <DOMAIN_ID>

Task:
Promote technical facts and technical rules into business rules for this domain.

Read:
- atlas/facts/technical-facts.yaml
- atlas/domains/<DOMAIN_ID>/technical-facts.yaml if present
- atlas/domains/<DOMAIN_ID>/04-technical-rules-backend.yaml
- atlas/domains/<DOMAIN_ID>/04-technical-rules-frontend.yaml
- atlas/domains/<DOMAIN_ID>/05-contract-mapping.yaml
- atlas/domains/<DOMAIN_ID>/10-contradictions.yaml if present
- atlas/map/validation-map.yaml
- atlas/map/permission-map.yaml
- atlas/map/state-map.yaml
- atlas/map/error-map.yaml

Write:
- atlas/domains/<DOMAIN_ID>/06-business-rules.yaml

Rules:
- Every business rule must derive from one or more technical rules and, where available, technical facts.
- Do not create unsupported business rules directly from intuition.
- Include enforcement summary: frontend/backend/database/data-access.
- Mark frontend-only, backend-only, and cross-layer rules.
- Preserve stable IDs if rerunning.
- Use confidence high only where facts/rules have strong evidence.
- Mark `needs_review: true` for inferred business meaning or low-confidence facts.
- If frontend and backend conflict, create or reference a contradiction rather than hiding it.

Good business rules are concise, business-readable, and still traceable.

Example:
Technical fact: The backend restricts knowledge search by accessible set IDs.
Business rule: Users may only search knowledge within sets they are permitted to access.
