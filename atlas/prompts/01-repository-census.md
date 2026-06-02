You are acting as a Principal Solutions Architect and Technical Writer.

You are reverse-engineering a mature React/TypeScript frontend and FastAPI/Pydantic backend into a bottom-up Requirements Hierarchy Pyramid.

Follow:
- atlas/config/project.yaml
- atlas/config/extraction-policy.md

Do not invent requirements. Preserve uncertainty.

# Phase 01 — Repository Census

Task:
Create a repository census for both repositories.

Do not infer final requirements yet.

Read `atlas/config/project.yaml` to find repository paths.

For the frontend, identify:
- routes/pages
- major feature folders
- API client modules
- custom hooks
- state stores
- form validation schemas
- permission/feature-flag logic
- major domain-specific components

For the backend, identify:
- FastAPI routers
- endpoint methods and paths
- Pydantic request/response models
- service modules
- repository/data access modules
- auth/permission dependencies
- background jobs
- integration clients
- tests

Write:
- atlas/global/frontend-inventory.yaml
- atlas/global/backend-inventory.yaml
- atlas/global/endpoint-index.yaml
- atlas/global/ui-route-index.yaml
- atlas/global/initial-domain-candidates.yaml

Rules:
- Every item must include file path and symbol name where applicable.
- Mark likely domain.
- Mark confidence high/medium/low.
- Do not create business rules or user stories yet.
