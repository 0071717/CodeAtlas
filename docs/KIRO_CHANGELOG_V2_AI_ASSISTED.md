# Kiro Changelog — V2 AI-Assisted Extraction Update

This file supplements `docs/KIRO_CHANGELOG.md` for the AI-assisted extraction improvements.

## 2026-06-05 — AI-assisted bounded extraction and React stack mapping

### Summary

CodeAtlas V2 now explicitly supports a hybrid extraction strategy:

```text
deterministic foundation first
→ bounded AI-assisted enrichment
→ validation and adversarial review
→ targeted next tasks
```

The intent is to move faster without waiting for perfect TypeScript or Python parser coverage, while still keeping evidence, confidence, and `needs_review` discipline.

### Added docs

- `docs/AI_ASSISTED_EXTRACTION_STRATEGY.md`
  - Defines when AI-assisted extraction is appropriate.
  - Requires bounded source slices, evidence, confidence, and validation.

- `docs/REACT_UI_STACK_MAPPING.md`
  - Specializes UI extraction for React, TypeScript, React Router DOM, TanStack Query, and Material UI.
  - Defines route, query, mutation, MUI form/action/state, and UI flow mapping targets.

- `docs/TASK_DECOMPOSITION_PLAYBOOK.md`
  - Defines how to break extraction/tooling work into small Kiro-executable tasks.

### Added prompts

- `atlas/prompts/framework/09-ai-assisted-extraction-worker.md`
- `atlas/prompts/framework/10-react-stack-ui-mapper.md`
- `atlas/prompts/framework/11-bounded-backend-flow-mapper.md`
- `atlas/prompts/framework/12-task-slicer.md`

### Updated guidance

- `docs/KIRO_ZIP_HANDOFF.md`
  - Now tells Kiro to read the AI-assisted extraction strategy, React stack mapping guide, and task decomposition playbook.
  - Adds current frontend assumptions: React, TypeScript, React Router DOM, TanStack Query, and Material UI.

### Recommended next workflow

1. Run the deterministic V2 foundation suite.
2. Pick one UI route/page cluster.
3. Run the React stack UI mapper prompt on that slice.
4. Pick the linked backend endpoint.
5. Run the bounded backend flow mapper prompt.
6. Validate outputs.
7. Run adversarial review.
8. Generate test candidates for that single route/API flow pair.

### Important note

AI-assisted extraction is allowed, but it is not automatically trusted. Claims still need evidence, confidence, `needs_review`, and validation.
