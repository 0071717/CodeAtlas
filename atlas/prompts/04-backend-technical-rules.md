You are acting as a Principal Solutions Architect and Technical Writer.

You are reverse-engineering a mature React/TypeScript frontend and FastAPI/Pydantic backend into a bottom-up Requirements Hierarchy Pyramid.

Follow:
- atlas/config/project.yaml
- atlas/config/extraction-policy.md
- docs/CODE_MAP_FOUNDATION.md

Do not invent requirements. Preserve uncertainty.

# Phase 04 — Backend Technical Rules

Domain: <DOMAIN_ID>

Task:
Extract backend technical rules for exactly this domain using the semantic Code Map and technical facts as the primary foundation.

Read first:
- atlas/domains/<DOMAIN_ID>/00-domain-scope.yaml
- atlas/map/backend-map.yaml
- atlas/map/api-map.yaml
- atlas/map/schema-map.yaml
- atlas/map/call-graph.yaml
- atlas/map/data-access-map.yaml
- atlas/map/validation-map.yaml
- atlas/map/permission-map.yaml
- atlas/map/error-map.yaml
- atlas/map/state-map.yaml
- atlas/facts/technical-facts.yaml

Read raw backend files only when map/fact evidence needs verification or line-level code references are missing.

Write:
- atlas/domains/<DOMAIN_ID>/01-backend-inventory.yaml
- atlas/domains/<DOMAIN_ID>/03-code-references.json
- atlas/domains/<DOMAIN_ID>/04-technical-rules-backend.yaml

Extract backend technical rules from:
- FastAPI endpoints
- request/response models
- Pydantic validators
- auth/permission dependencies
- service-layer conditions
- helper/service calls
- repository/database constraints
- OS/OpenSearch/data-access behaviour such as `*_os.py`
- exceptions and error codes
- state transitions
- side effects
- background jobs

Required traversal:
router endpoint
→ request model
→ auth/permission dependency
→ service function
→ helper/service calls
→ OS/OpenSearch/data-access layer
→ response model
→ errors/side effects

Rules:
- Every technical rule must derive from technical facts and/or Code Map evidence where possible.
- Every technical rule must cite code references.
- Technical rule format: "The backend [does something] when/if [condition]."
- Do not infer business intent yet.
- Preserve stable IDs if rerunning.
- Use confidence high only when directly evidenced.
- Use `needs_review: true` when the map or code evidence is incomplete.
- Do not stop at router files; service and data-access behaviour is often where business behaviour is implemented.
