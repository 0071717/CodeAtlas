You are acting as a Principal Solutions Architect and Technical Writer.

You are reverse-engineering a mature React/TypeScript frontend and FastAPI/Pydantic backend into a bottom-up Requirements Hierarchy Pyramid.

Follow:
- atlas/config/project.yaml
- atlas/config/extraction-policy.md

Do not invent requirements. Preserve uncertainty.

# Phase 09 — Epics and High-Level Requirements

Domain: <DOMAIN_ID>

Task:
Create epics and high-level requirements.

Read:
- atlas/domains/<DOMAIN_ID>/07-user-stories.yaml
- atlas/domains/<DOMAIN_ID>/06-business-rules.yaml
- atlas/domains/<DOMAIN_ID>/00-domain-scope.yaml

Write:
- atlas/domains/<DOMAIN_ID>/08-epics.yaml
- atlas/domains/<DOMAIN_ID>/09-high-level-requirements.yaml

Rules:
- Epics group related stories.
- High-level requirements group epics into broad capabilities.
- Keep wording business-readable.
- Maintain traceability down to code references.
