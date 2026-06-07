# CodeAtlas Codex Phase Prompts

Use one prompt at a time. Do not ask Codex to implement multiple phases unless you intentionally want a larger, harder-to-review patch.

## Generic prompt

```text
You are working in the 0071717/CodeAtlas repository.

Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md first.

Continue from the current repository state.

Implement only Phase <NN> - <PHASE TITLE>.

Use AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md as the durable product contract and roadmap.

Do not implement later phases.
Do not weaken strict validation, evidence requirements, write policy, status taxonomy, or canonical/derived separation to make tests pass.

Run the relevant phase exit gate.

Stop after the phase exit gate passes.

If blocked, report:
- what changed
- what passed
- what failed
- exact failing command/output
- files likely responsible
- next recommended fix
```

## Phase prompts

### Phase 00

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master. Implement only Phase 00 - Strict canonical execution and run manifest. Add or update the tests needed for this phase. Run the Phase 00 exit gate. Do not start Phase 01. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 01

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 00. Implement only Phase 01 - Evidence and provenance envelope. Add or update the tests needed for this phase. Run the Phase 01 exit gate. Do not start Phase 02. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 02

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 01. Implement only Phase 02 - Canonical write-path enforcement. Add or update the tests needed for this phase. Run the Phase 02 exit gate. Do not start Phase 03. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 03

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 02. Implement only Phase 03 - Sub-agent task/output contract and promotion gate. Add or update the tests needed for this phase. Run the Phase 03 exit gate. Do not start Phase 04. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 04

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 03. Implement only Phase 04 - Schema/artifact validation hardening. Add or update the tests needed for this phase. Run the Phase 04 exit gate. Do not start Phase 05. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 05

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 04. Implement only Phase 05 - RIG-inspired build/test intelligence graph. Add or update the tests needed for this phase. Run the Phase 05 exit gate. Do not start Phase 06. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 06

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 05. Implement only Phase 06 - Parser-backed Python/FastAPI extraction. Add or update the tests needed for this phase. Run the Phase 06 exit gate. Do not start Phase 07. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 07

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 06. Implement only Phase 07 - Parser-backed TypeScript/React extraction. Add or update the tests needed for this phase. Run the Phase 07 exit gate. Do not start Phase 08. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 08

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 07. Implement only Phase 08 - SCIP/LSP-style symbol import. Add or update the tests needed for this phase. Run the Phase 08 exit gate. Do not start Phase 09. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 09

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 08. Implement only Phase 09 - OpenAPI ingestion and source comparison. Add or update the tests needed for this phase. Run the Phase 09 exit gate. Do not start Phase 10. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 10

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 09. Implement only Phase 10 - Graph traversal policies and authoritative trace refusal. Add or update the tests needed for this phase. Run the Phase 10 exit gate. Do not start Phase 11. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 11

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 10. Implement only Phase 11 - SQLite read model as derived-only compiled view. Add or update the tests needed for this phase. Run the Phase 11 exit gate. Do not start Phase 12. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 12

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 11. Implement only Phase 12 - Task-shaped context commands. Add or update the tests needed for this phase. Run the Phase 12 exit gate. Do not start Phase 13. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 13

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 12. Implement only Phase 13 - Git intelligence and risk signals. Add or update the tests needed for this phase. Run the Phase 13 exit gate. Do not start Phase 14. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 14

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 13. Implement only Phase 14 - External findings import: SARIF/CodeQL/Semgrep. Add or update the tests needed for this phase. Run the Phase 14 exit gate. Do not start Phase 15. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 15

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 14. Implement only Phase 15 - Runtime/business-truth evidence loop. Add or update the tests needed for this phase. Run the Phase 15 exit gate. Do not start Phase 16. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 16

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 15. Implement only Phase 16 - Capability gaps as first-class blockers. Add or update the tests needed for this phase. Run the Phase 16 exit gate. Do not start Phase 17. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 17

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 16. Implement only Phase 17 - Kiro and legacy prompt-first quarantine. Add or update the tests needed for this phase. Run the Phase 17 exit gate. Do not start Phase 18. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 18

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 17. Implement only Phase 18 - Security hardening. Add or update the tests needed for this phase. Run the Phase 18 exit gate. Do not start Phase 19. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 19

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 18. Implement only Phase 19 - Performance and incremental indexing. Add or update the tests needed for this phase. Run the Phase 19 exit gate. Do not start Phase 20. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 20

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 19. Implement only Phase 20 - Evaluation benchmark. Add or update the tests needed for this phase. Run the Phase 20 exit gate. Do not start Phase 21. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 21

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 20. Implement only Phase 21 - Documentation, migration, and deprecation cleanup. Add or update the tests needed for this phase. Run the Phase 21 exit gate. Do not start Phase 22. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 22

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 21. Implement only Phase 22 - CI enforcement. Add or update the tests/workflows needed for this phase. Run the Phase 22 exit gate or report which GitHub Actions checks cannot be run locally. Do not start Phase 23. If blocked, report the exact failing command/output and likely files responsible.
```

### Phase 23

```text
Read AGENTS.md and docs/CODEX_IMPLEMENTATION_PLAN.md. Continue from current master after Phase 22. Implement only Phase 23 - Minimum trustworthy version release gate. Add or update the tests, reports, and release-readiness checks needed for this phase. Run the Phase 23 release gate. If blocked, report the exact failing command/output and likely files responsible.
```
