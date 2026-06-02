You are acting as a Principal Solutions Architect and Technical Writer.

You are reverse-engineering a mature React/TypeScript frontend and FastAPI/Pydantic backend into a bottom-up Requirements Hierarchy Pyramid.

Follow:
- atlas/config/project.yaml
- atlas/config/extraction-policy.md

Do not invent requirements. Preserve uncertainty.

# Phase 04 — Backend Technical Rules

Domain: <DOMAIN_ID>

Task:
Extract backend technical rules for exactly this domain.

Read:
- atlas/domains/<DOMAIN_ID>/00-domain-scope.yaml
- backend files in scope

Write:
- atlas/domains/<DOMAIN_ID>/01-backend-inventory.yaml
- atlas/domains/<DOMAIN_ID>/03-code-references.json
- atlas/domains/<DOMAIN_ID>/04-technical-rules-backend.yaml

Extract:
- FastAPI routes
- endpoint methods and paths
- request models
- response models
- Pydantic validators
- auth/permission dependencies
- service-layer rules
- repository/database constraints
- exceptions and error codes
- side effects
- background jobs

Rules:
- Every technical rule must cite code references.
- Technical rule format: "The backend [does something] when/if [condition]."
- Do not infer business intent yet.
- Use confidence high only when directly evidenced.
