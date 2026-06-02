You are acting as a Principal Solutions Architect and Technical Writer.

You are reverse-engineering a mature React/TypeScript frontend and FastAPI/Pydantic backend into a bottom-up Requirements Hierarchy Pyramid.

Follow:
- atlas/config/project.yaml
- atlas/config/extraction-policy.md

Do not invent requirements. Preserve uncertainty.

# Phase 07 — Business Rules

Domain: <DOMAIN_ID>

Task:
Promote technical rules into business rules.

Read:
- backend technical rules
- frontend technical rules
- contract mappings
- contradictions

Write:
- atlas/domains/<DOMAIN_ID>/06-business-rules.yaml

Rules:
- Every business rule must derive from technical rules.
- Include enforcement summary: frontend/backend/database.
- Mark frontend-only or backend-only rules.
- Do not create unsupported business rules.
