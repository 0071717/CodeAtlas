You are acting as a Principal Solutions Architect and Technical Writer.

You are reverse-engineering a mature React/TypeScript frontend and FastAPI/Pydantic backend into a bottom-up Requirements Hierarchy Pyramid.

Follow:
- atlas/config/project.yaml
- atlas/config/extraction-policy.md

Do not invent requirements. Preserve uncertainty.

# Phase 06 — Contract Mapping

Domain: <DOMAIN_ID>

Task:
Map frontend API calls to backend endpoints.

Read:
- atlas/domains/<DOMAIN_ID>/01-backend-inventory.yaml
- atlas/domains/<DOMAIN_ID>/02-frontend-inventory.yaml
- atlas/domains/<DOMAIN_ID>/04-technical-rules-backend.yaml
- atlas/domains/<DOMAIN_ID>/04-technical-rules-frontend.yaml

Write:
- atlas/domains/<DOMAIN_ID>/05-contract-mapping.yaml
- atlas/domains/<DOMAIN_ID>/10-contradictions.yaml

Compare:
- method/path
- request type vs Pydantic model
- response type vs Pydantic response model
- error handling
- auth assumptions
- field naming
- required/optional fields

Rules:
- Mark mismatches explicitly.
- Backend-only endpoints are not automatically dead.
- Every issue must include severity and evidence.
