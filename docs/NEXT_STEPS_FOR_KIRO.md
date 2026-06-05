# Next Steps for Kiro

Use this after pulling the latest CodeAtlas framework changes into an Amazon Workspace or other local workspace that already has generated Atlas artifacts.

## Situation

The full Atlas framework may already have been run, and local Kiro/Claude work may have modified CodeAtlas prompts, scripts, and generated outputs.

Do **not** rerun the entire framework from the beginning yet.

Instead:

```text
1. preserve the current generated outputs
2. normalize them into atlas/knowledge
3. reverse-check generated claims against code evidence
4. refresh Kiro context packs and steering files
5. inspect unsupported claims and targeted rerun recommendations
6. rerun only weak layers/domains
```

## First command

From the CodeAtlas repo root:

```bash
chmod +x atlas/scripts/*.sh 2>/dev/null || true
bash atlas/scripts/run-post-extraction-suite.sh
```

This runs:

```text
atlas/scripts/run-knowledge-normalizer.sh
atlas/scripts/run-reverse-verification.sh
atlas/scripts/run-context-refresh.sh
```

## Review outputs

After the suite, inspect:

```text
atlas/knowledge/README.md
atlas/knowledge/manifest.yaml
atlas/knowledge/audit/evidence-chain-audit.md
atlas/knowledge/audit/reverse-verification-report.md
atlas/knowledge/audit/unsupported-claims.md
atlas/knowledge/audit/confidence-report.md
atlas/knowledge/audit/targeted-rerun-plan.md
atlas/context-packs/context-refresh-report.md
.kiro/steering/codeatlas-context.md
.kiro/steering/codeatlas-rules.md
.kiro/steering/codeatlas-review-guidance.md
.kiro/steering/codeatlas-debugging-guidance.md
```

## Copy-paste prompt for Kiro

```text
You are working in my local CodeAtlas workspace.

Context:
I have already run the full Atlas framework once and generated maps, facts, technical rules, business rules, user stories, epics, high-level requirements, audits, and context outputs. Kiro/Claude may also have modified the framework locally.

Do not rerun the full framework from the beginning yet.

Goal:
Make the existing generated Atlas artifacts accurate, machine-readable, and useful for future Kiro code answers, debugging, feature work, tests, merge-request reviews, and a future UI.

Read first:
- docs/KIRO_CHANGELOG.md
- docs/NEXT_STEPS_FOR_KIRO.md
- docs/KNOWLEDGE_CONTEXT_LAYER.md
- docs/CODE_ATLAS_REVERSE_VERIFICATION.md
- docs/KIRO_CONTEXT_USAGE.md
- docs/MERGE_REQUEST_REVIEW_FRAMEWORK.md
- docs/YAML_CONTRACT.md
- docs/CODE_MAP_FOUNDATION.md
- atlas/config/extraction-policy.md

Then run:

bash atlas/scripts/run-post-extraction-suite.sh

After it completes, review:
- atlas/knowledge/audit/evidence-chain-audit.md
- atlas/knowledge/audit/reverse-verification-report.md
- atlas/knowledge/audit/unsupported-claims.md
- atlas/knowledge/audit/targeted-rerun-plan.md
- atlas/context-packs/context-refresh-report.md

Rules:
1. Treat current generated Atlas outputs as a baseline candidate, not approved truth.
2. Normalize current outputs into atlas/knowledge.
3. Reverse-check generated claims against source-code evidence.
4. If source code conflicts with generated Atlas context, trust source code and mark the generated node stale or needs_review.
5. Do not invent requirements or missing evidence.
6. Preserve stable IDs, confidence, needs_review, and review state.
7. Prefer targeted reruns over full framework reruns.
8. Refresh context packs and .kiro/steering so future Kiro sessions use atlas/knowledge first.
9. Do not post merge-request comments unless I explicitly approve.
10. Any AI-generated MR comment must start with: ✦ AI GENERATED REVIEW

Deliverables:
- atlas/knowledge/* normalized outputs
- atlas/knowledge/audit/* verification reports
- refreshed atlas/context-packs/*
- refreshed .kiro/steering/*
- a short summary of what is reliable, what is weak, and what should be rerun next
```

## Decision tree after the suite

| Finding | Action |
|---|---|
| Knowledge layer missing or malformed | rerun `run-knowledge-normalizer.sh` |
| Many unsupported claims | rerun reverse verification, then targeted domain extraction |
| Map nodes stale or wrong | rerun map/facts for impacted domain |
| Weak business rules | rerun business-rule derivation from technical rules |
| Weak stories/epics/HLRs | rerun story/epic/HLR derivation only |
| Frontend/backend contract drift | rerun API/schema/contract mapping and contradiction scan |
| Architecture discovery wrong globally | then rerun architecture discovery and foundation |

## Merge-request review command

Draft-only review:

```bash
bash atlas/scripts/run-mr-review.sh <mr_iid>
```

Approved posting mode, only after human review:

```bash
export CODEATLAS_REVIEW_MODE=approved-post
export CODEATLAS_POST_REVIEW_COMMENTS=true
export CODEATLAS_REVIEW_APPROVED=true
bash atlas/scripts/run-mr-review.sh <mr_iid>
```

Default mode must not post comments.

## Source of truth for future UI

The future UI should consume:

```text
atlas/knowledge/graph/requirements-graph.json
atlas/knowledge/graph/cytoscape-elements.json
atlas/knowledge/cards/*.json
atlas/knowledge/indexes/*.yaml
```

The UI should not parse random Markdown as its source of truth.
