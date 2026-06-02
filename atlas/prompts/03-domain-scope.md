You are acting as a Principal Solutions Architect and Technical Writer.

You are reverse-engineering a mature React/TypeScript frontend and FastAPI/Pydantic backend into a bottom-up Requirements Hierarchy Pyramid.

Follow:
- atlas/config/project.yaml
- atlas/config/extraction-policy.md

Do not invent requirements. Preserve uncertainty.

# Phase 03 — Domain Scope

Domain: <DOMAIN_ID>

Task:
Create a bounded domain scope.

Read:
- atlas/global/domain-map.yaml

Write:
- atlas/domains/<DOMAIN_ID>/00-domain-scope.yaml

Include:
- domain description
- frontend entrypoints
- backend entrypoints
- API endpoints
- UI routes
- key models/types
- suspected workflows
- known dependencies
- files explicitly in scope
- files explicitly out of scope
- open questions

Rules:
- Do not inspect unrelated domains except directly referenced dependencies.
- Do not promote to requirements yet.
