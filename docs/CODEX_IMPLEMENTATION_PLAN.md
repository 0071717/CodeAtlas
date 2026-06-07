# CodeAtlas Codex Implementation Plan

This is the durable Codex roadmap for CodeAtlas. Codex must read this file and the root `AGENTS.md` before making changes.

## Product contract

CodeAtlas is a deterministic-first code evidence compiler and AI-grounding orchestrator.

CodeAtlas is not another coding agent. It is the evidence boundary that coding agents operate inside.

The goal is to make AI coding agents less wrong by forcing them to operate inside a verified evidence boundary.

## Trust model

CodeAtlas has two layers:

```text
Tier 1: Canonical Evidence Layer
  deterministic extraction only
  source/provenance snapshot
  file hashes and source spans
  parser-backed symbols/routes/endpoints/contracts
  validated facts, edges, flows, and manifests
  explicit capability gaps and stale-state detection

Tier 2: Derived Intelligence Layer
  context packs
  impact analysis
  trace exploration
  review risk
  likely relevant tests
  AI/sub-agent findings
  summaries and explanations
```

Only Tier 1 can be canonical. Tier 2 must preserve status, evidence, confidence, known unknowns, capability gaps, and refusal rules.

## Required vocabularies

Statuses:

```text
verified
inferred
unsupported
stale
contradicted
partial
unknown
```

Confidence values:

```text
high
medium
low
none
```

Evidence kinds:

```text
source_span
openapi_operation
test_definition
test_result
runtime_trace
git_history
config_value
generated_artifact
human_review
llm_finding
external_finding
```

Status and confidence are separate. A high-confidence inferred claim is still not verified.

## Evidence and artifact requirements

Every source-backed canonical claim must resolve to evidence containing:

```text
evidence_id
evidence_kind
source_commit
repo
file_path
file_hash
span.start_line
span.end_line
span.start_col
span.end_col
snippet_hash
extractor.id
extractor.version
extractor.kind
```

Every canonical artifact must have an envelope containing:

```text
schema_version
artifact_id
artifact_kind
generated_at
generator.id
generator.version
generator.command
source.repo
source.source_commit
source.dirty_worktree
source.file_manifest_hash
validation.status
validation.validated_at
validation.validator
validation.errors
validation.warnings
data
```

## Write policy

No direct writes to canonical paths. All canonical writes must go through guarded artifact IO.

Sub-agents and Kiro may only write structured findings into inbox/quarantine paths. Promotion into canonical knowledge must happen only through deterministic validation and promotion commands.

## Strict mode

Canonical commands should support `--strict`.

Strict mode must fail closed on invalid JSON, schema mismatch, missing artifact envelope, missing evidence, stale source hash, bad snippet hash, broken graph reference, unknown edge type, unknown node type, unknown status, unknown confidence, unknown evidence kind, missing capability gap for unsupported patterns, generated read model from invalid artifacts, and context pack from invalid or stale artifacts.

## Implementation phases

Implement phases in order. Do not skip exit gates. Do not start the next phase unless the prompt explicitly asks for it.

| Phase | Name | Core outcome |
|---:|---|---|
| 00 | Strict canonical execution and run manifest | strict mode, fail-closed ordering, run manifest |
| 01 | Evidence and provenance envelope | shared evidence/provenance/artifact envelope helpers |
| 02 | Canonical write-path enforcement | guarded writes and static write audit |
| 03 | Sub-agent task/output contract and promotion gate | structured findings, validation, promotion, quarantine |
| 04 | Schema/artifact validation hardening | blocking validation and controlled vocabularies |
| 05 | RIG-inspired build/test intelligence graph | deterministic build/test topology graph |
| 06 | Parser-backed Python/FastAPI extraction | AST-backed backend extraction |
| 07 | Parser-backed TypeScript/React extraction | TypeScript Compiler API-backed frontend extraction |
| 08 | SCIP/LSP-style symbol import | optional external symbol/reference import |
| 09 | OpenAPI ingestion and source comparison | HTTP contract evidence and contradiction detection |
| 10 | Graph traversal policies and authoritative trace refusal | deterministic trace/review/test traversal policies |
| 11 | SQLite read model as derived-only compiled view | SQLite compiles only from validated artifacts |
| 12 | Task-shaped context commands | trace, review-risk, tests-for-change, why, gaps |
| 13 | Git intelligence and risk signals | churn, co-change, ownership, reviewer/risk signals |
| 14 | External findings import | SARIF/CodeQL/Semgrep as external findings |
| 15 | Runtime/business-truth evidence loop | scoped runtime/test/requirement-backed claims |
| 16 | Capability gaps as first-class blockers | unsupported patterns block authoritative claims |
| 17 | Kiro and legacy prompt-first quarantine | Kiro enriches through findings only |
| 18 | Security hardening | prompt injection, secrets, paths, shell safety |
| 19 | Performance and incremental indexing | cache/invalidation/incremental plans |
| 20 | Evaluation benchmark | measure unsupported authoritative claims |
| 21 | Documentation, migration, deprecation cleanup | docs match enforced behavior and legacy quarantine |
| 22 | CI enforcement | trust rules enforced in GitHub Actions |
| 23 | Minimum trustworthy version release gate | release-readiness gate and reports |

## Common Codex workflow

For every phase:

1. Read `AGENTS.md`.
2. Read this file.
3. Inspect the existing implementation before editing.
4. Implement only the requested phase.
5. Add or update tests.
6. Run the phase exit gate from the prompt.
7. Stop after the phase passes or report the blocker.

## Blocker report format

If blocked, report:

```text
- what was changed
- what passed
- what failed
- exact failing command/output
- files likely responsible
- next recommended fix
```
