# Read-only Rules

Default child-agent mode is read-only.

Allowed behavior:

- inspect supplied context,
- call permitted `ngk tool ... --json` commands,
- read relevant non-sensitive files when necessary,
- return structured findings and uncertainty.

Forbidden behavior unless the task contract explicitly enables write mode:

- modifying source files,
- altering repository state,
- installing dependencies,
- committing or publishing changes,
- spawning nested orchestration.
