You are acting as a senior software architect performing architecture discovery.

Goal:
Analyze the configured frontend and backend repositories and produce editable architecture briefs that a human can review, correct, and approve before CodeAtlas extraction begins.

Read:
- atlas/config/project.yaml

Write:
- atlas/architecture-discovery/backend-architecture-draft.md
- atlas/architecture-discovery/frontend-architecture-draft.md
- atlas/architecture-discovery/cross-repo-architecture-draft.md
- atlas/architecture-discovery/architecture-evidence.yaml
- atlas/architecture-discovery/architecture-open-questions.md

Also update, but clearly mark as draft:
- .kiro/steering/backend-patterns.md
- .kiro/steering/frontend-patterns.md
- .kiro/steering/architecture.md
- .kiro/steering/structure.md

Backend architecture discovery:
- Identify router files and naming conventions.
- Identify how routers are registered with FastAPI.
- Identify endpoint-to-service call patterns.
- Identify service layer naming conventions.
- Identify whether services call other services.
- Identify helper/util modules.
- Identify OS/OpenSearch/data-access layer files, especially `*_os.py`.
- Identify Pydantic schema/model locations.
- Identify validators, enums, shared DTOs, request/response models.
- Identify auth, permissions, dependencies, middleware.
- Identify error handling style.
- Identify background jobs, tasks, integrations.
- Identify test structure.
- Identify generated code and folders to exclude.
- Identify the canonical backend request lifecycle.

Frontend architecture discovery:
- Identify routing framework and route definitions.
- Identify page/layout structure.
- Identify feature/domain folder structure.
- Identify API client layer and HTTP client conventions.
- Identify how frontend API calls map to backend routes.
- Identify React Query/SWR/Redux/Zustand/Context/local state patterns.
- Identify form libraries and validation libraries.
- Identify component hierarchy patterns.
- Identify auth/permission/feature flag patterns.
- Identify error handling and notification/toast patterns.
- Identify type generation/manual TypeScript type patterns.
- Identify test structure.
- Identify generated code and folders to exclude.
- Identify canonical frontend user interaction lifecycle.

Cross-repo discovery:
- Identify how frontend and backend contracts are linked.
- Identify OpenAPI/schema generation if present.
- Identify shared naming conventions.
- Identify high-level domain naming.
- Identify likely domain boundaries.
- Identify mismatches or ambiguity in architecture assumptions.

Rules:
1. Do not extract requirements yet.
2. Do not create user stories, epics, or business rules.
3. Focus only on architecture, conventions, and traversal paths.
4. Every major claim must include evidence: file path, symbol/pattern, and confidence.
5. Mark uncertain claims as "Needs review".
6. Prefer practical extraction guidance over generic architecture prose.
7. The output must be useful as context for later Kiro sessions.
8. Do not blindly trust existing comments or README files; verify against code.
9. Do not scan generated folders unless necessary.
10. Produce concise but detailed architecture drafts.
