# Start Here for Kiro

You are reading CodeAtlas, a framework for turning mature application code into deterministic, evidence-backed, machine-readable project knowledge for AI agents, developer tools, reviewers, test generators, visualizers, and `ngk` CLI workflows.

## First rule

**Use the V2 deterministic path first.**

Do not start a new target project with the old prompt-first extraction pipeline.

The canonical first-run path is:

```bash
python3 atlas/tools/codeatlas_v2_canonical.py doctor
python3 atlas/tools/codeatlas_v2_canonical.py all
```

or:

```bash
bash atlas/scripts/run-pre-transfer-check.sh
bash atlas/scripts/run-framework-v2-suite.sh
```

## Read first

Read these files before making framework changes or running extraction:

```text
README.md
docs/CANONICAL_EXECUTION_PATH.md
docs/LEGACY_AND_EXPERIMENTAL_PATHS.md
docs/PRE_TRANSFER_READINESS_CHECKLIST.md
docs/KIRO_ZIP_HANDOFF.md
docs/FRAMEWORK_ARCHITECTURE_V2.md
docs/LAYER_BUILD_CONTRACT.md
docs/KIRO_FRAMEWORK_IMPLEMENTATION_GUIDE.md
docs/NGK_ECOSYSTEM_HARDENING_PLAN.md
docs/NGK_TRACE_VISUAL_FLOW_EXPLORER.md
docs/TOOL_SUITE_V2.md
docs/GRAPHIFY_PATTERNS_ADOPTED.md
docs/REPO_CLEANUP_AUDIT.md
atlas/config/project.yaml
atlas/config/project.schema.json
atlas/config/ecosystem-bindings.yaml
```

## What CodeAtlas is trying to build

```text
source/provenance
→ deterministic indexes
→ payload/DSL reconstruction
→ semantic maps
→ ecosystem bindings
→ runtime context
→ graph/contracts
→ explicit error flows
→ conditional flows
→ facts/rules/requirements
→ testing/coverage
→ normalized knowledge
→ verification/challenge
→ downstream tools such as ngk trace
```

## What not to do first

Do not run these as the first step unless the user explicitly selects the legacy path:

```text
bash atlas/scripts/run-auto.sh
bash atlas/scripts/run-pilot-auto.sh
bash atlas/scripts/run-foundation.sh
```

These older workflows may still be useful for exploration, but deterministic V2 artifacts should be created first.

## If generated artifacts already exist

Before trusting them, run:

```bash
python3 atlas/tools/codeatlas_v2_canonical.py doctor
python3 atlas/tools/codeatlas_v2_canonical.py validate
python3 atlas/tools/codeatlas_graph_report.py
```

Then inspect:

```text
atlas/audit/preflight-doctor-report.json
atlas/audit/artifact-json-promotion-report.json
atlas/audit/v2-validation-report.json
atlas/visualizer/GRAPH_REPORT.md
atlas/source/
atlas/index/
atlas/graph/
atlas/flows/
atlas/audit/
```

If source code conflicts with Atlas artifacts, source code wins. Mark Atlas stale, unsupported, contradicted, or `needs_review: true`.

## Kiro operating rules

1. Prefer deterministic scripts and graph traversal before AI interpretation.
2. Do not derive business rules directly from raw code if maps/flows/facts are missing.
3. Preserve stable IDs.
4. Every claim must have evidence or `needs_review: true`.
5. Treat `confidence: low` and `needs_review: true` as non-authoritative.
6. Do not treat frontend-only validation as backend enforcement.
7. Do not treat backend-only endpoints as dead without evidence.
8. Do not invent OpenSearch Query DSL clauses.
9. Do not hide missing links; emit findings.
10. Do not modify application repos unless explicitly requested.

## When building new framework pieces

Use bounded tasks. For each task define:

```text
goal
inputs
outputs
schema
builder
validator
acceptance criteria
known limitations
follow-up tasks
```

## Current high-priority implementation gaps

```text
TypeScript AST / ts-morph frontend extraction
FastAPI router/dependency materialisation
OpenSearch Query DSL reconstruction
explicit Python/React error-flow extraction
symbol-level drift planning
SQLite/DuckDB/Kuzu derived read models
```

Do not spend effort on high-level requirements generation until these foundations are stronger.

## Useful commands

```bash
python3 atlas/tools/codeatlas_v2_canonical.py doctor
python3 atlas/tools/codeatlas_v2_canonical.py all
python3 atlas/tools/codeatlas_v2_canonical.py validate
python3 atlas/tools/codeatlas_v2_canonical.py drift-check
python3 atlas/tools/codeatlas_graph_report.py
python3 atlas/tools/codeatlas_query.py query "claims endpoint"
python3 atlas/tools/codeatlas_query.py explain "POST /claims"
python3 atlas/tools/codeatlas_query.py path "claims route" "claims endpoint"
python3 atlas/tools/ngk_trace_regraph_exporter.py "POST /claims"
```

## Done means

A framework task is done when:

```text
outputs are deterministic where possible
validation can be run
limitations are documented
changelog is updated
next targeted task is clear
```
