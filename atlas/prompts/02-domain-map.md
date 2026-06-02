You are acting as a Principal Solutions Architect and Technical Writer.

You are reverse-engineering a mature React/TypeScript frontend and FastAPI/Pydantic backend into a bottom-up Requirements Hierarchy Pyramid.

Follow:
- atlas/config/project.yaml
- atlas/config/extraction-policy.md

Do not invent requirements. Preserve uncertainty.

# Phase 02 — Domain Map

Task:
Using the repository census, create a domain map.

Group code artifacts by business capability, not folder structure.

Read:
- atlas/global/frontend-inventory.yaml
- atlas/global/backend-inventory.yaml
- atlas/global/initial-domain-candidates.yaml

Write:
- atlas/global/domain-map.yaml

Each domain must include:
- id
- name
- description
- frontend files
- backend files
- UI routes
- API endpoints
- key schemas/types
- key services
- confidence
- open questions

Rules:
- Prefer smaller cohesive domains over giant domains.
- Mark shared infrastructure as `cross_cutting`.
- Files may have primary and secondary domains.
- Do not extract detailed requirements yet.
