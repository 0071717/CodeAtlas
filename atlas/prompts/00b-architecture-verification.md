You are acting as an architecture verification agent.

Goal:
Review the architecture drafts and verify them against the repositories. Improve accuracy, mark uncertainty, and prepare steering files for CodeAtlas extraction.

Read:
- atlas/config/project.yaml
- atlas/architecture-discovery/backend-architecture-draft.md
- atlas/architecture-discovery/frontend-architecture-draft.md
- atlas/architecture-discovery/cross-repo-architecture-draft.md
- atlas/architecture-discovery/architecture-evidence.yaml
- atlas/architecture-discovery/architecture-open-questions.md

Write:
- atlas/architecture-discovery/backend-architecture-verified.md
- atlas/architecture-discovery/frontend-architecture-verified.md
- atlas/architecture-discovery/cross-repo-architecture-verified.md
- atlas/architecture-discovery/extraction-traversal-guide.md
- atlas/architecture-discovery/human-review-checklist.md

Update:
- .kiro/steering/backend-patterns.md
- .kiro/steering/frontend-patterns.md
- .kiro/steering/architecture.md
- .kiro/steering/structure.md

Rules:
1. Treat the draft as a hypothesis, not truth.
2. Verify using code evidence.
3. Mark each major architecture claim as:
   - Verified
   - Likely
   - Needs review
   - Incorrect
4. If incorrect, explain the corrected pattern.
5. Produce an extraction traversal guide that later agents can follow.
6. Do not extract requirements yet.
7. Do not create business rules or user stories.
