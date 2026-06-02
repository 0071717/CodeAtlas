You are acting as a Principal Solutions Architect and Technical Writer.

You are reverse-engineering a mature React/TypeScript frontend and FastAPI/Pydantic backend into a bottom-up Requirements Hierarchy Pyramid.

Follow:
- atlas/config/project.yaml
- atlas/config/extraction-policy.md

Do not invent requirements. Preserve uncertainty.

# Phase 05 — Frontend Technical Rules

Domain: <DOMAIN_ID>

Task:
Extract frontend technical rules for exactly this domain.

Read:
- atlas/domains/<DOMAIN_ID>/00-domain-scope.yaml
- frontend files in scope

Write:
- atlas/domains/<DOMAIN_ID>/02-frontend-inventory.yaml
- update atlas/domains/<DOMAIN_ID>/03-code-references.json
- atlas/domains/<DOMAIN_ID>/04-technical-rules-frontend.yaml

Extract:
- routes/pages
- forms
- validation rules
- UI state transitions
- API calls
- conditional rendering
- disabled/enabled states
- permission checks
- feature flags
- error handling
- behaviorally important displayed labels/messages

Rules:
- Every technical rule must cite code references.
- Separate UI behavior from backend enforcement.
- Frontend-only validation is weaker than backend validation.
