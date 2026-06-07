# Codex Task Template

## Task title

<phase title>

## Mandatory context

Before making changes:

1. Read `AGENTS.md`.
2. Read `docs/CODEX_IMPLEMENTATION_PLAN.md`.
3. Read this task file or the prompt for the current phase.
4. Inspect the existing implementation before editing.
5. Implement only this task.
6. Do not start later phases.
7. Do not weaken validation, trust states, write policy, or evidence requirements to make tests pass.

## Product contract reminder

CodeAtlas is a deterministic-first code evidence compiler and AI-grounding orchestrator.

CodeAtlas is not another coding agent. It is the evidence boundary that coding agents operate inside.

Make AI coding agents less wrong by forcing them to operate inside a verified evidence boundary.

## Problem

<exact problem>

## Required implementation

<exact implementation steps>

## Files to inspect/change

```text
<files>
```

## Acceptance criteria

```text
<criteria>
```

## Tests to add

```text
<tests>
```

## Commands to run

```bash
<commands>
```

## Stop condition

Stop after this phase passes its exit gate.

Do not start the next phase.

If blocked, produce a concise report containing:

```text
- what was changed
- what passed
- what failed
- exact failing command/output
- files likely responsible
- next recommended fix
```
