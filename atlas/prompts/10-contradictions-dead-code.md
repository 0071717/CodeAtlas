You are acting as a Principal Solutions Architect and Technical Writer.

You are reverse-engineering a mature React/TypeScript frontend and FastAPI/Pydantic backend into a bottom-up Requirements Hierarchy Pyramid.

Follow:
- atlas/config/project.yaml
- atlas/config/extraction-policy.md

Do not invent requirements. Preserve uncertainty.

# Phase 10 — Contradictions and Dead-Code Candidates

Domain: <DOMAIN_ID>

Task:
Triangulate contradictions and dead-code candidates.

Read all domain artifacts.

Write:
- atlas/domains/<DOMAIN_ID>/10-contradictions.yaml
- atlas/domains/<DOMAIN_ID>/11-dead-code-candidates.yaml

Check:
- frontend/backend validation mismatch
- permission mismatch
- response shape mismatch
- error handling gaps
- state/status mismatches
- orphan frontend API calls
- backend-only endpoints
- unused frontend components/hooks/API clients
- unused backend services/schemas/repository methods

Rules:
- Backend-only endpoint is not automatically dead.
- Use severity critical/high/medium/low.
- Provide evidence and recommended action.
