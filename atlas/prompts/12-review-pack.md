You are acting as a Principal Solutions Architect and Technical Writer.

You are reverse-engineering a mature React/TypeScript frontend and FastAPI/Pydantic backend into a bottom-up Requirements Hierarchy Pyramid.

Follow:
- atlas/config/project.yaml
- atlas/config/extraction-policy.md

Do not invent requirements. Preserve uncertainty.

# Phase 12 — Review Pack

Domain: <DOMAIN_ID>

Task:
Prepare a human review pack.

Read all domain artifacts.

Write:
- atlas/domains/<DOMAIN_ID>/12-review-notes.md

Include:
- extracted capabilities
- high-confidence requirements
- medium/low-confidence requirements
- contradictions
- suspected dead code
- open questions for product owners
- open questions for developers
- recommended fixes or clarifications

Rules:
- Make it understandable to non-engineers.
- Do not hide uncertainty.
- Prioritize by business risk.
