# Extraction Policy

## Core principle

Never reverse-engineer the whole application in one pass.

Work domain by domain.

## Pyramid order

Always extract in this order:

1. Code References
2. Technical Rules
3. Contract Mappings
4. Business Rules
5. User Stories
6. Epics
7. High-Level Requirements
8. Contradictions / Dead-Code Candidates
9. Review Pack
10. Kiro Steering Updates

## Evidence rules

- Every technical rule must cite one or more code references.
- Every business rule must derive from one or more technical rules.
- Every user story must derive from one or more business rules.
- Every epic must derive from user stories.
- Every high-level requirement must derive from epics.
- Do not invent requirements unsupported by code.

## Frontend/backend authority

- Backend is authoritative for auth, permission enforcement, persistence, server validation, and side effects.
- Frontend is authoritative for visible UI behavior, navigation, local state, and form interaction.
- Frontend-only validation is not considered strong business enforcement unless backend agrees.

## Contradictions

Contradictions are first-class outputs. Do not hide them in notes.

Examples:
- Frontend sends a field the backend does not accept.
- Frontend marks a field optional but backend requires it.
- Frontend hides an admin action but backend does not enforce admin permission.
- Backend returns an error the frontend does not handle.
- State names differ between frontend and backend.

## Dead code

Backend endpoints not called by frontend are not automatically dead. Mark them as `backend_only_endpoint` unless route registration, tests, and references prove they are unused.
