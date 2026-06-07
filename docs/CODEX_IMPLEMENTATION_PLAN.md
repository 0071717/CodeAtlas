# CodeAtlas Codex Implementation Plan

This document is the durable implementation plan for Codex tasks in this repository.

Codex must also read the root `AGENTS.md` file before making changes.

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

Only Tier 1 can be canonical.

Tier 2 must preserve status, evidence, confidence, known unknowns, capability gaps, and refusal rules.

## Required statuses

Use only:

```text
verified
inferred
unsupported
stale
contradicted
partial
unknown
```

## Required confidence values

Use only:

```text
high
medium
low
none
```

Status and confidence are separate. A high-confidence inferred claim is still not verified.

## Required evidence kinds

Use only:

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

## Required source-backed evidence fields

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

## Required artifact envelope fields

Every canonical artifact must contain:

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

## Canonical write rule

No direct writes to canonical paths.

All canonical writes must go through guarded artifact IO.

Sub-agents and Kiro may only write structured findings into inbox/quarantine paths.

Promotion into canonical knowledge must happen only through deterministic validation and promotion commands.

## Canonical paths

```text
atlas/source/
atlas/index/
atlas/payloads/
atlas/bindings/
atlas/runtime/
atlas/graph/
atlas/errors/
atlas/flows/
atlas/facts/
atlas/rules/
atlas/testing/
atlas/knowledge/
atlas/audit/
atlas/change/
atlas/visualizer/
```

## Sub-agent and Kiro paths

Sub-agents may write only to:

```text
atlas/agents/inbox/
atlas/agents/logs/
atlas/agents/quarantine/
```

Kiro may write only to:

```text
atlas/kiro/inbox/
atlas/kiro/findings/
atlas/kiro/quarantine/
atlas/context-packs/
```

## Strict mode

Canonical commands should support `--strict`.

Strict mode must fail closed on:

```text
invalid JSON
schema mismatch
missing artifact envelope
missing evidence
stale source hash
bad snippet hash
broken graph reference
unknown edge type
unknown node type
unknown status
unknown confidence
unknown evidence kind
missing capability gap for unsupported patterns
generated read model from invalid artifacts
context pack from invalid or stale artifacts
```

## Required implementation order

Implement phases in order. Do not skip exit gates.

```text
Phase 00 - Strict canonical execution and run manifest
Phase 01 - Evidence and provenance envelope
Phase 02 - Canonical write-path enforcement
Phase 03 - Sub-agent task/output contract and promotion gate
Phase 04 - Schema/artifact validation hardening
Phase 05 - RIG-inspired build/test intelligence graph
Phase 06 - Parser-backed Python/FastAPI extraction
Phase 07 - Parser-backed TypeScript/React extraction
Phase 08 - SCIP/LSP-style symbol import
Phase 09 - OpenAPI ingestion and source comparison
Phase 10 - Graph traversal policies and authoritative trace refusal
Phase 11 - SQLite read model as derived-only compiled view
Phase 12 - Task-shaped context commands
Phase 13 - Git intelligence and risk signals
Phase 14 - External findings import: SARIF/CodeQL/Semgrep
Phase 15 - Runtime/business-truth evidence loop
Phase 16 - Capability gaps as first-class blockers
Phase 17 - Kiro and legacy prompt-first quarantine
Phase 18 - Security hardening
Phase 19 - Performance and incremental indexing
Phase 20 - Evaluation benchmark
Phase 21 - Documentation, migration, and deprecation cleanup
Phase 22 - CI enforcement
Phase 23 - Minimum trustworthy version release gate
```

## Phase 00 exit gate

```bash
python3 atlas/tools/codeatlas_v2_canonical.py doctor --strict
python3 atlas/tools/codeatlas_v2_canonical.py all --strict
pytest -q tests/test_canonical_strict_mode.py tests/test_run_manifest.py tests/test_strict_pipeline_order.py
```

## Phase 01 exit gate

```bash
pytest -q tests/test_evidence_span_hash.py tests/test_artifact_envelope_required.py tests/test_artifact_atomic_write.py tests/test_artifact_path_policy.py
python3 atlas/tools/codeatlas_v2_canonical.py all --strict
```

## Phase 02 exit gate

```bash
python3 atlas/tools/codeatlas_write_audit.py --strict
pytest -q tests/test_write_policy*.py tests/test_write_audit_static_scan.py
```

## Phase 03 exit gate

```bash
python3 atlas/tools/codeatlas_subagent_validate.py tests/fixtures/subagents/valid.findings.json
python3 atlas/tools/codeatlas_promote_findings.py --inbox tests/fixtures/subagents --dry-run --strict
pytest -q tests/test_subagent*.py tests/test_promotion*.py tests/test_kiro_findings_are_not_canonical.py
```

## Phase 04 exit gate

```bash
python3 atlas/tools/validate_artifacts.py --strict
pytest -q tests/test_all_artifacts_schema_valid.py tests/test_edge_type_registry.py tests/test_fact_schema_generator_alignment.py
```

## Phase 05 exit gate

```bash
python3 atlas/tools/codeatlas_build_test_graph.py --strict
python3 atlas/tools/validate_artifacts.py --strict
pytest -q tests/test_build_test_graph.py tests/test_pyproject_build_graph.py tests/test_package_json_build_graph.py
```

## Phase 06 exit gate

```bash
python3 atlas/tools/codeatlas_python_index.py --strict
python3 atlas/tools/validate_artifacts.py --strict
pytest -q tests/test_python_extractor.py tests/test_fastapi_*.py
```

## Phase 07 exit gate

```bash
python3 atlas/tools/codeatlas_ts_index.py --strict
python3 atlas/tools/validate_artifacts.py --strict
pytest -q tests/test_typescript_extractor.py tests/test_ts_*.py
```

## Phase 08 exit gate

```bash
python3 atlas/tools/codeatlas_scip_import.py --strict || true
pytest -q tests/test_scip_import.py
```

## Phase 09 exit gate

```bash
python3 atlas/tools/codeatlas_openapi_ingest.py --strict
python3 atlas/tools/codeatlas_openapi_compare.py --strict
pytest -q tests/test_openapi_*.py
```

## Phase 10 exit gate

```bash
python3 atlas/tools/codeatlas_context_pack.py trace "POST /claims" --strict
python3 atlas/tools/ngk_trace_regraph_exporter.py "POST /claims" --strict
pytest -q tests/test_trace_*.py tests/test_traversal_policy.py
```

## Phase 11 exit gate

```bash
python3 atlas/tools/codeatlas_sqlite_read_model.py --strict
pytest -q tests/test_sqlite_*.py
```

## Phase 12 exit gate

```bash
python3 atlas/tools/codeatlas_context_pack.py trace "POST /claims" --strict
python3 atlas/tools/codeatlas_context_pack.py capability-gaps . --strict
pytest -q tests/test_context_pack*.py tests/test_task_commands.py
```

## Phase 13 exit gate

```bash
python3 atlas/tools/codeatlas_git_intelligence.py --strict
python3 atlas/tools/codeatlas_context_pack.py review-risk main..HEAD --strict
pytest -q tests/test_git_*.py tests/test_review_risk_context.py
```

## Phase 14 exit gate

```bash
python3 atlas/tools/codeatlas_sarif_import.py --input tests/fixtures/sarif/sample.sarif --strict
pytest -q tests/test_sarif_*.py tests/test_semgrep_import.py tests/test_codeql_import.py
```

## Phase 15 exit gate

```bash
python3 atlas/tools/codeatlas_test_results_import.py --strict
python3 atlas/tools/codeatlas_runtime_import.py --strict
python3 atlas/tools/codeatlas_requirement_import.py --strict
pytest -q tests/test_runtime_business_truth.py tests/test_business_*.py
```

## Phase 16 exit gate

```bash
python3 atlas/tools/codeatlas_capability_audit.py --strict
pytest -q tests/test_capability_gaps.py tests/test_gap_*.py
```

## Phase 17 exit gate

```bash
python3 atlas/tools/codeatlas_kiro_import.py --input tests/fixtures/kiro/valid.json --strict
python3 atlas/tools/codeatlas_write_audit.py --strict
pytest -q tests/test_kiro_*.py
```

## Phase 18 exit gate

```bash
python3 atlas/tools/codeatlas_security_audit.py --strict
pytest -q tests/test_security.py tests/test_prompt_injection_wrapped.py tests/test_secret_redaction.py
```

## Phase 19 exit gate

```bash
python3 atlas/tools/codeatlas_incremental_plan.py --strict
pytest -q tests/test_incremental_*.py
```

## Phase 20 exit gate

```bash
python3 benchmarks/harness.py --mode codeatlas_context_pack --strict
python3 benchmarks/grade_answers.py --strict
pytest -q tests/test_benchmark_*.py
```

## Phase 21 exit gate

```bash
python3 atlas/tools/codeatlas_migrate_artifacts.py --from legacy --to v2 --quarantine-invalid --strict
pytest -q tests/test_migration_*.py tests/test_docs_examples.py
```

## Phase 22 exit gate

All GitHub Actions jobs pass.

## Phase 23 release gate

```bash
python3 atlas/tools/codeatlas_v2_canonical.py all --strict
python3 atlas/tools/validate_artifacts.py --strict
python3 atlas/tools/codeatlas_write_audit.py --strict
python3 atlas/tools/codeatlas_security_audit.py --strict
python3 benchmarks/harness.py --mode codeatlas_context_pack --smoke --strict
python3 benchmarks/grade_answers.py --smoke --strict
pytest -q
```

## Work rule for Codex

For every Codex task:

1. Read `AGENTS.md`.
2. Read this file.
3. Implement only the requested phase.
4. Add or update tests.
5. Run the phase exit gate.
6. Stop after the phase passes or report the blocker.
