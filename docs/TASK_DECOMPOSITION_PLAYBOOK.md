# Task Decomposition Playbook

CodeAtlas and Kiro should build knowledge in small, reviewable tasks.

Reliable pattern:

```text
discover
→ select one bounded slice
→ extract deterministic candidates
→ enrich with AI if useful
→ validate
→ write findings
→ recommend the next slice
```

## Good slice sizes

```text
one React route/page cluster
one form and its mutation hook
one backend endpoint and service path
one service function plus direct callees
one domain folder
one test file cluster
one config/search schema group
one visualizer view
```

Avoid slices like entire frontend, entire backend, all requirements, all tests, or all business rules.

## Standard task fields

Each task should define:

```text
id
type
goal
input artifacts
source files allowed
output artifacts
acceptance criteria
validator
known limitations
follow-up task
```

## Kiro worker rule

Each Kiro worker should implement only one task. If the task reveals a larger issue, write a follow-up task instead of expanding scope.

## Acceptance gate

A task is complete when:

```text
output artifacts were written
validation was run or limitation recorded
uncertain claims are marked needs_review
next task is documented
changelog is updated if framework behaviour changed
```

## Recommended first extraction task sequence

```text
1. Snapshot and file index all configured repos.
2. Build symbol, route, endpoint, API-client, and test candidate indexes.
3. Pick one high-value frontend route.
4. Map its React Router page/component cluster.
5. Map its TanStack Query hooks and API clients.
6. Map its Material UI forms/actions/states.
7. Link UI API client to backend endpoint candidate.
8. Map the backend endpoint/service/data path.
9. Generate one UI flow and one API request flow.
10. Run validator and adversarial review.
11. Generate test candidates for that single flow.
```

## Example bounded task

```yaml
task:
  id: task.frontend.claims.create_flow
  type: ai_assisted_frontend_mapping
  goal: Map the create-claim UI flow.
  inputs:
    - atlas/index/route-index.yaml
    - atlas/index/api-client-index.yaml
  outputs:
    - atlas/map/component-map.yaml
    - atlas/map/form-map.yaml
    - atlas/map/ui-state-map.yaml
    - atlas/flows/ui-flows.yaml
  acceptance_criteria:
    - route is linked to page component
    - form fields and submit action are captured
    - query or mutation hook is captured if present
    - API client is linked or marked needs_review
    - loading/error/success states are captured or marked missing
    - every claim has evidence or needs_review
```
