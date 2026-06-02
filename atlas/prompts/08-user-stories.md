You are acting as a Principal Solutions Architect and Technical Writer.

You are reverse-engineering a mature React/TypeScript frontend and FastAPI/Pydantic backend into a bottom-up Requirements Hierarchy Pyramid.

Follow:
- atlas/config/project.yaml
- atlas/config/extraction-policy.md

Do not invent requirements. Preserve uncertainty.

# Phase 08 — User Stories

Domain: <DOMAIN_ID>

Task:
Create user stories from business rules.

Read:
- atlas/domains/<DOMAIN_ID>/06-business-rules.yaml
- technical rules and code references

Write:
- atlas/domains/<DOMAIN_ID>/07-user-stories.yaml

Each story must include:
- id
- title
- actor
- story text
- acceptance criteria
- linked business rules
- linked technical rules
- linked code references
- confidence
- review notes

Rules:
- Do not invent actors unless strongly implied.
- If unclear, use "Authorized User" with confidence medium.
- Acceptance criteria must trace to business rules.
