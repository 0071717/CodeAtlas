You are acting as a Principal Solutions Architect and Technical Writer.

You are reverse-engineering a mature React/TypeScript frontend and FastAPI/Pydantic backend into a bottom-up Requirements Hierarchy Pyramid.

Follow:
- atlas/config/project.yaml
- atlas/config/extraction-policy.md
- docs/CODE_MAP_FOUNDATION.md

Do not invent requirements. Preserve uncertainty.

# Phase 05 — Frontend Technical Rules

Domain: <DOMAIN_ID>

Task:
Extract frontend technical rules for exactly this domain using the semantic Code Map and technical facts as the primary foundation.

Read first:
- atlas/domains/<DOMAIN_ID>/00-domain-scope.yaml
- atlas/map/frontend-map.yaml
- atlas/map/ui-flow-map.yaml
- atlas/map/api-map.yaml
- atlas/map/validation-map.yaml
- atlas/map/permission-map.yaml
- atlas/map/error-map.yaml
- atlas/map/state-map.yaml
- atlas/facts/technical-facts.yaml

Read raw frontend files only when map/fact evidence needs verification or line-level code references are missing.

Write:
- atlas/domains/<DOMAIN_ID>/02-frontend-inventory.yaml
- update atlas/domains/<DOMAIN_ID>/03-code-references.json
- atlas/domains/<DOMAIN_ID>/04-technical-rules-frontend.yaml

Extract frontend technical rules from:
- routes/pages
- page/component hierarchy
- hooks/state
- form validation
- API calls
- API client payload construction
- conditional rendering
- disabled/enabled states
- permission checks
- feature flags
- loading/error/success/empty states
- behaviorally important labels/messages

Required traversal:
route
→ page/layout
→ component
→ hook/state/form
→ API client
→ backend endpoint
→ loading/error/success UI behaviour

Rules:
- Every technical rule must derive from technical facts and/or Code Map evidence where possible.
- Every technical rule must cite code references.
- Separate UI behavior from backend enforcement.
- Frontend-only validation is weaker than backend validation.
- Preserve stable IDs if rerunning.
- Use confidence high only when directly evidenced.
- Use `needs_review: true` when the map or code evidence is incomplete.
