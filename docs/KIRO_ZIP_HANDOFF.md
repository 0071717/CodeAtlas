# Kiro Zip Handoff Instructions

Use this document when CodeAtlas is provided to Kiro as a zip, copied workspace, or fresh clone.

## What you are looking at

CodeAtlas is not an application repo. It is a framework for reverse-engineering one or more application/config/test repos into a deterministic, evidence-backed project knowledge base.

The goal is to help Kiro answer questions, debug, plan features, generate tests, review merge requests, detect drift, visualize the codebase, and safely improve the project.

## Read first

Read these files before changing anything:

```text
README.md
docs/FRAMEWORK_ARCHITECTURE_V2.md
docs/KIRO_FRAMEWORK_IMPLEMENTATION_GUIDE.md
docs/LAYER_BUILD_CONTRACT.md
docs/AST_EXTRACTION_STRATEGY.md
docs/MULTI_REPO_MAPPING_STRATEGY.md
docs/RUNTIME_CONTEXT_MAPPING.md
docs/TESTING_ARCHAEOLOGY.md
docs/VERIFICATION_AND_CHALLENGE_LAYER.md
docs/TARGETED_RERUN_ENGINE.md
docs/UI_UX_IMPLEMENTATION_GUIDE.md
docs/KIRO_CHANGELOG.md
atlas/config/extraction-policy.md
```

## Your first job

Do not immediately run the legacy full extraction pipeline.

First inspect whether the workspace already contains generated Atlas artifacts:

```text
atlas/source/
atlas/index/
atlas/map/
atlas/graph/
atlas/flows/
atlas/facts/
atlas/rules/
atlas/requirements/
atlas/testing/
atlas/knowledge/
atlas/audit/
atlas/change/
```

Then decide:

```text
No generated artifacts exist
→ run deterministic V2 foundation first.

Some old map/fact/domain artifacts exist
→ preserve them, run validation/normalization, then targeted refresh.

Knowledge layer exists
→ validate it before trusting it.

Source code conflicts with Atlas context
→ source code wins; mark Atlas stale or unsupported.
```

## Preferred first commands

From the CodeAtlas root:

```bash
python3 atlas/tools/codeatlas_v2_suite.py init
python3 atlas/tools/codeatlas_v2_suite.py snapshot
python3 atlas/tools/codeatlas_v2_suite.py validate
python3 atlas/tools/codeatlas_v2_suite.py visualizer-export
```

Or use:

```bash
bash atlas/scripts/run-framework-v2-suite.sh
```

If a configured project repo is missing, write a clear finding instead of guessing paths.

## What CodeAtlas V2 is trying to build

```text
source/provenance
→ deterministic file/symbol indexes
→ runtime entrypoint indexes
→ semantic architecture maps
→ runtime/cross-cutting maps
→ relationship and contract graphs
→ conditional API/UI/data/error flows
→ evidence-backed technical facts
→ rules and requirements
→ testing and coverage models
→ normalized knowledge layer
→ verification/challenge reports
→ tool outputs and visualizer data
→ change impact and targeted reruns
```

## Kiro operating rules

1. Prefer deterministic scripts and graph traversal before AI interpretation.
2. Do not derive business rules directly from raw code if facts/rules can be derived from maps/flows.
3. Preserve stable IDs.
4. Every claim must have evidence or `needs_review: true`.
5. Treat `confidence: low` or `needs_review: true` as non-authoritative.
6. Do not treat frontend-only validation as backend enforcement.
7. Do not treat backend-only endpoints as dead code without evidence.
8. Do not modify application repos unless explicitly requested.
9. Do not regenerate the entire corpus when targeted rerun is enough.
10. If source code and Atlas disagree, trust source code and emit a stale/unsupported finding.

## When building new framework pieces

Use bounded tasks. Do not build everything in one Kiro response.

For each task, define:

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

Write small composable scripts. Prefer tools that can be run locally without cloud services.

## When building UI

Read `docs/UI_UX_IMPLEMENTATION_GUIDE.md`. Build from fixture JSON produced by `visualizer-export` first. Do not make the UI parse random Markdown. The UI should consume compact JSON exports under `atlas/visualizer/` and `atlas/knowledge/graph/`.

## Done means

A framework change is not done until:

```text
outputs are schema-shaped and deterministic where possible
validation can be run
limitations are documented
Kiro changelog is updated
handoff instructions remain accurate
next targeted tasks are clear
```
