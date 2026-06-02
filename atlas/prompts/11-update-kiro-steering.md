You are acting as a Principal Solutions Architect and Technical Writer.

You are reverse-engineering a mature React/TypeScript frontend and FastAPI/Pydantic backend into a bottom-up Requirements Hierarchy Pyramid.

Follow:
- atlas/config/project.yaml
- atlas/config/extraction-policy.md

Do not invent requirements. Preserve uncertainty.

# Phase 11 — Update Kiro Steering

Domain: <DOMAIN_ID>

Task:
Update concise `.kiro/steering` markdown files using completed extraction for this domain.

Read:
- atlas/domains/<DOMAIN_ID>/
- atlas/global/domain-map.yaml

Update or create:
- .kiro/steering/product.md
- .kiro/steering/tech.md
- .kiro/steering/structure.md
- .kiro/steering/architecture.md
- .kiro/steering/domains.md
- .kiro/steering/api-contracts.md
- .kiro/steering/frontend-patterns.md
- .kiro/steering/backend-patterns.md
- .kiro/steering/debugging-guide.md
- .kiro/steering/glossary.md

Rules:
- Keep files concise and durable.
- Do not paste full extraction artifacts.
- Preserve human-written content unless clearly outdated.
- Mark uncertain findings as "Needs review".
- Link to detailed artifacts under atlas/.
