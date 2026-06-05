# UI/UX Implementation Guide for Kiro

Kiro often performs better at UI work when the task is framed as a user journey with explicit states, not as a vague component request.

## UI design rules

```text
Start from the user task.
Identify the primary action.
Identify secondary and destructive actions.
Make loading, empty, error, success, and permission-denied states explicit.
Use existing design system/components first.
Avoid creating new styling conventions unless asked.
Prefer clear flows over dense dashboards.
Design for realistic data volume.
Preserve accessibility.
```

## React implementation rules

```text
Keep API calls in API clients/hooks.
Separate data fetching from presentational components.
Use explicit states: idle, loading, success, error, empty.
Handle server errors intentionally.
Do not rely only on console errors.
Do not duplicate backend business enforcement unless needed for UX.
Frontend validation supports UX; backend remains authoritative.
Use semantic labels and accessible controls.
Add stable test IDs only when semantic selectors are insufficient.
```

## Required UI state checklist

For every mapped or generated screen, identify:

```text
initial state
loading state
empty state
populated state
validation error state
server error state
permission denied state
success state
navigation/redirect state
disabled state
unsaved/dirty state when relevant
```

## Testability checklist

```text
important controls are selectable
forms have accessible labels
visible errors can be asserted
loading state can be asserted
success state can be asserted
API calls can be mocked
route can be opened directly
test data requirements are documented
```

## Kiro UI prompt shape

Before coding UI, Kiro should answer:

```text
What is the user trying to do?
What route/page/component owns the flow?
What data/API contract is needed?
What states must be handled?
What existing design system/patterns should be reused?
What tests should be added or updated?
What Atlas artifacts may need rerun?
```

## Visualizer UI guidance

A future CodeAtlas visualizer should consume compact JSON exports under `atlas/visualizer/` and `atlas/knowledge/graph/`. It should not parse arbitrary Markdown.

Useful views:

```text
domain view
API flow view
UI flow view
contract view
test coverage view
change impact view
requirement trace view
confidence/staleness overlay
```
