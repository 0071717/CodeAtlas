# Kiro Changelog — V2 Contract and Testing Workers

This supplements the main Kiro changelog.

## 2026-06-05 — Contract mapper and UI-flow test worker

### Added prompts

- `atlas/prompts/framework/13-ui-api-contract-mapper.md`
  - Maps one frontend API client or TanStack Query hook to one backend endpoint candidate.
  - Writes contract graph, UI-to-API graph, API/schema maps, and mismatch findings.

- `atlas/prompts/framework/14-playwright-from-ui-flow-worker.md`
  - Generates Playwright test candidates from one evidenced UI flow.
  - Produces test candidates, selector review needs, and test data needs.

### Recommended use

Run these after one bounded UI flow and the linked backend endpoint have been mapped:

```text
1. React stack UI mapper
2. UI/API contract mapper
3. Bounded backend flow mapper
4. Validator worker
5. Adversarial reviewer
6. Playwright from UI flow worker
```

### Rule

Do not generate UI tests from guesses. Generate them from route, form, action, state, API client, endpoint, or flow evidence.
