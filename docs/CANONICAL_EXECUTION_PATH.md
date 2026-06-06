# Canonical Execution Path

This document defines the canonical CodeAtlas execution path for Kiro and downstream `ngk` use.

## Current decision

The **V2 deterministic path is canonical**.

The older prompt-first extraction pipeline remains available as legacy/experimental context, but it is not the default path for a new target project.

## Why

The deterministic path gives Kiro and `ngk` stable filesystem artifacts before AI enrichment:

```text
source snapshot
→ file/hash index
→ symbol/endpoint/route/API/test indexes
→ graph seeds
→ flow seeds
→ payload/error/fact/knowledge seed layers
→ validation/drift reports
→ visualizer exports
→ targeted AI enrichment
→ reverse verification
```

This reduces hallucination and makes outputs reviewable, diffable, and reusable.

## First commands in a fresh transferred workspace

From the CodeAtlas repo root:

```bash
python3 atlas/tools/codeatlas_v2_canonical.py doctor
python3 atlas/tools/codeatlas_v2_canonical.py all
python3 atlas/tools/ngk_trace_regraph_exporter.py "POST /example" || true
```

or:

```bash
bash atlas/scripts/run-pre-transfer-check.sh
bash atlas/scripts/run-framework-v2-suite.sh
```

The placeholder trace may fail if no target project has an endpoint matching `POST /example`; that is acceptable. The goal is to confirm the tool exists and fails cleanly.

`codeatlas_v2_canonical.py all` now runs the deterministic suite, promotes JSON-compatible legacy `.yaml` artifacts to `.json`, builds the local graph report, and runs artifact validation.

Manual helper commands:

```bash
python3 atlas/tools/codeatlas_v2_canonical.py graph-report
python3 atlas/tools/codeatlas_v2_canonical.py validate-artifacts
python3 atlas/tools/codeatlas_query.py query "claims endpoint"
python3 atlas/tools/codeatlas_query.py explain "POST /claims"
python3 atlas/tools/codeatlas_query.py path "claims route" "claims endpoint"
```

## Canonical artifacts

The canonical source-of-truth artifacts are file-based and local:

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
atlas/requirements/
atlas/testing/
atlas/knowledge/
atlas/audit/
atlas/change/
atlas/visualizer/
```

## Legacy path

The older scripts and prompts can still be useful for exploratory Kiro work, but they should not be the first run in a new workspace. See `docs/LEGACY_AND_EXPERIMENTAL_PATHS.md`.

## AI usage rule

Kiro may use AI to enrich bounded packets, summarize findings, derive rules, and challenge claims. Kiro must not invent code facts, endpoint paths, query DSL clauses, permission enforcement, UI states, or business rules without evidence.

## Review rule

If source code and generated Atlas artifacts disagree, source code wins. The Atlas artifact must be marked stale, unsupported, contradicted, or `needs_review: true`.
