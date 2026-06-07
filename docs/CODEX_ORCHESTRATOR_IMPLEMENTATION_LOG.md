# Codex Orchestrator Implementation Log

This log records implementation decisions, safe partials, blockers, and verification for the no-MCP ngk orchestrator work.

## Decisions

- MCP remains disabled for canonical workflows. Generated Kiro agents set `includeMcpJson: false` and shell tools are constrained to `ngk tool` commands.
- Kiro authentication is configurable; `KIRO_API_KEY` is not mandatory unless `kiro.require_api_key` is true.
- Missing Atlas caches or optional deterministic engines return warning JSON with `capability_gap` rather than fabricated facts.
- Write-agent interfaces are dry-run/read-only by default; source modifications are not enabled by the orchestrator.
- Child-agent claims are untrusted until schema validation and verification gates pass.

## Phase status


## Implemented phases

### O0 — Kiro capability probe and configurable headless runner

Implemented `ngk_orchestrator.kiro.capability_probe`, `HeadlessRunner`, `ngk kiro probe`, and `ngk kiro config show`. The runner builds least-privilege commands using `--trust-tools=read,grep` by default, captures stdout/stderr/exit/duration, and handles missing binaries/timeouts. Blocker: no `kiro-cli` binary exists in this environment, so probe returns warning JSON rather than executing Kiro.

### O1 — Contract schemas and orchestration storage

Implemented lightweight schema files, agent-result validation, orchestration storage layout, event log, and `ngk orchestrations list/show/init-test`. Validation is deterministic and implemented in Python rather than adding a JSON Schema runtime dependency.

### O2 — `ngk tool` JSON facade

Implemented shell JSON facade commands for sources, facts, traces, impact, tests, contract checks/boundary, drift, result verification, and context. Missing optional caches/engines return warning JSON with capability gaps.

### O3 — Agent profiles and Kiro custom-agent generation

Added canonical ngk YAML profiles, prompt templates, shared agent rules, and generated Kiro JSON artifacts with `includeMcpJson=false`, least-privilege shell commands, hooks, and denied nested orchestration/write/install commands.

### O4 — Kiro hooks framework

Added hook templates and install/validate/test-event commands. Hooks enforce read-only behavior, block secret reads, restrict shell to `ngk tool ...`, audit tool events, and require `<ngk_agent_result>`.

### O5 — Per-agent context builder

Implemented context-pack JSON/Markdown generation with task identity, scope, verified Atlas facts, changed files, deterministic analysis, labeled other-agent claims, inferred observations, forbidden assumptions, output contract, and prompt-injection warning. Selection is intentionally compact and heuristic where richer Atlas tracing is unavailable.

### O6 — Delegate command and child runner integration

Implemented `ngk delegate ...` commands with `--no-agent`, `--strict`, `--json`, mock-agent support, env propagation, output capture, result parsing, audit writing, and strict failure behavior.

### O7 — Planner and scheduler

Implemented preflight, deterministic analysis, changed-file task planning, simple sequential scheduler, critic inclusion when agents run, synthesis inclusion, and event lifecycle logging. Max-parallel budget is represented but execution remains sequential as the safest deterministic-first partial.

### O8 — UI/API overlap and cross-stack review

Implemented heuristic boundary detection and `ngk tool contract boundary --changed --json`. Weak field mappings become uncertainties/warnings. Rich UI-component/API-route trace matching is limited by available Atlas artifacts.

### O9 — Verification gate and critic plumbing

Implemented `ngk_orchestrator.engine.verifier`, `ngk verify-result`, `ngk critic latest`, schema checks, fact existence/evidence checks, stale-evidence strict behavior, support-label rules, inferred-reason checks, and not-confirmed rejection.

### O10 — Conflict detection and synthesis

Implemented duplicate/contradiction/confidence-mismatch detection, synthesis acceptance/rejection gates, confidence-preserving summary behavior, `ngk synthesize latest`, `ngk conflicts latest`, and summary sections.

### O11 — Full read-only orchestrated review workflow

Implemented end-to-end `ngk orchestrate review --changed` including preflight, deterministic analysis, planning, context building, optional mock child runs, audit, critic, conflict detection, synthesis, and summary output.

### O12 — Smart terminal orchestration view

Implemented non-interactive smart orchestration cockpit output with status, summary, conflicts, synthesis, and event-log tail. Full TUI keyboard navigation is a remaining milestone because this environment is non-interactive.

### O13 — Implementation dry-run and write-safety interfaces

Implemented dry-run `ngk orchestrate implement`, write-disabled default, lock data structure, and worktree list placeholder. No source patch application is enabled.

### O14 — Orchestrator evals and adversarial fixtures

Implemented `ngk orchestrator eval list/run` deterministic eval facade and regression tests for schema, storage, runner command construction, hook guard behavior, and conflict detection. Fixture corpus is represented by eval case names; richer fixture files are a remaining hardening task.

## Final hardening notes

- Canonical MCP usage was not added. Generated agents explicitly set `includeMcpJson=false`.
- Generated shell allowed commands are only `ngk tool ...` prefixes.
- Generated denied commands include nested orchestration/delegation, git commit/push, destructive remove, installs, and `--trust-all-tools`.
- Context packs include prompt-injection warnings and label orchestrator observations as inferred/guidance.
- Known partials: real Kiro execution could not be exercised without a Kiro binary; planner boundary detection is heuristic when Atlas trace artifacts are sparse; smart view is non-interactive text rather than a keyboard TUI; write agents remain intentionally disabled.
