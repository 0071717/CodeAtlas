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
docs/CODEX_ATLAS_NGK_ENGINE_HANDOFF.md
docs/NGK_GENERATED_FRAMEWORK_BUNDLE_MANIFEST.md
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
→ downstream tools such as ngk trace, ngk impact, ngk verify-answer, ngk review, and ngk smart
```

## Trusted ngk engine direction

The new trusted-engine direction is captured in:

```text
docs/CODEX_ATLAS_NGK_ENGINE_HANDOFF.md
```

The implementation priority is:

```text
1. evidence contract and validators
2. citation/source-span index
3. drift detection
4. deterministic graph engine
5. UI/API impact analyzers
6. test selection
7. Kiro context packs
8. ngk verify-answer
9. eval suite
10. Atlas-native review
11. contract checks
12. smart terminal integration
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
python3 atlas/tools/codeatlas_v2_canonical.py validate-artifacts
python3 atlas/tools/codeatlas_v2_canonical.py graph-report
```

Then inspect:

```text
atlas/audit/preflight-doctor-report.json
atlas/audit/artifact-json-promotion-report.json
atlas/audit/v2-validation-report.json
atlas/audit/artifact-validation-report.json
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

Prefer adding deterministic artifact producers, validators, and read models before adding new AI prompts. AI prompts should consume Atlas artifacts and cite fact IDs, not replace deterministic extraction.
