# Repository Cleanup Audit

The canonical execution path is deterministic V2. The repository has already moved away from the old prompt-first default, but there are still legacy references to keep clearly separated from deterministic extraction.

## Canonical keep

Keep these prominent:

- `atlas/tools/codeatlas_v2_suite.py`
- `atlas/tools/codeatlas_v2_canonical.py`
- `atlas/tools/codeatlas_preflight_doctor.py`
- `atlas/tools/ngk_trace_regraph_exporter.py`
- `atlas/tools/react_stack_indexer.py`
- `atlas/tools/codeatlas_graph_report.py`
- `atlas/tools/codeatlas_query.py`
- `atlas/tools/validate_artifacts.py`
- `docs/CANONICAL_EXECUTION_PATH.md`
- `docs/FRAMEWORK_ARCHITECTURE_V2.md`
- `docs/LAYER_BUILD_CONTRACT.md`
- `docs/GRAPHIFY_PATTERNS_ADOPTED.md`

## Legacy / experimental

Treat these as legacy or future-oriented unless the user explicitly asks for them:

- old prompt-first `atlas/scripts/run-*.sh` wrappers that call Kiro phases directly
- `atlas/scripts/orchestrate_extraction.py`
- broad prompt suites for facts, rules, stories, epics, HLRs, release governance, and review packs
- old docs that position requirements generation as the default first objective

Do not delete them blindly. They may contain useful process knowledge. The cleanup goal is to stop Kiro from treating them as canonical.

## Generated-output safety

Generated Atlas artifacts can contain target-project structure, behaviour, query details, and test information. `.gitignore` now ignores generated outputs under deterministic artifact folders, visualizer outputs, audit/change outputs, higher-level legacy outputs, and local read models.

## Added in this cleanup pass

- `atlas/tools/codeatlas_graph_report.py`
- `atlas/tools/codeatlas_query.py`
- `atlas/tools/validate_artifacts.py`
- `docs/GRAPHIFY_PATTERNS_ADOPTED.md`
- stricter generated-artifact `.gitignore` rules

## Remaining gaps

- legacy `.yaml` artifact names inside the V2 suite
- graph report and artifact validation not yet wired into the canonical `all` command
- candidate-only React extraction
- missing FastAPI route materialisation
- missing endpoint-scoped dependency/middleware envelopes
- missing OpenSearch Query DSL reconstruction
- missing test coverage link extraction
- missing symbol-level drift and release baselines

## Recommended next cleanup commit

1. Update `atlas/tools/codeatlas_v2_canonical.py` so `all` also runs `codeatlas_graph_report.py` and `validate_artifacts.py`.
2. Update `ngk_trace_regraph_exporter.py` to prefer `.json` artifacts and fall back to legacy `.yaml`.
3. Add a README under `atlas/scripts/` that clearly marks prompt-first scripts as legacy/experimental.
4. Consider moving old prompt-first scripts to `atlas/legacy/scripts/` only after confirming no active docs depend on their current paths.
