# Kiro Context Usage Guide

This guide tells Kiro and other AI coding agents how to use generated CodeAtlas knowledge effectively for accurate code answers, debugging, feature work, tests, refactors, and merge-request reviews.

## Core rule

Do not blindly rescan the full codebase when CodeAtlas context exists.

Use generated context first, then inspect raw source code only for implementation details, missing evidence, or verification.

## Preferred context order

When answering a code question or planning a change, use this order:

1. `atlas/knowledge/manifest.yaml`
2. `atlas/knowledge/indexes/*.yaml`
3. `atlas/knowledge/cards/*.json`
4. `atlas/context-packs/*.md`
5. `.kiro/steering/*.md`
6. `atlas/knowledge/nodes/*.yaml`
7. `atlas/knowledge/edges.yaml`
8. `atlas/knowledge/audit/*.md`
9. original `atlas/map`, `atlas/facts`, and `atlas/domains` artifacts
10. raw source code, only when needed

## Task-specific guidance

### Debugging

Start with:

```text
atlas/knowledge/indexes/by_file.yaml
atlas/knowledge/indexes/by_domain.yaml
atlas/knowledge/cards/domain-cards.json
atlas/context-packs/debugging-context.md
.kiro/steering/codeatlas-debugging-guidance.md
```

Then trace:

```text
UI route → component → hook/state → API client → backend endpoint → service → data access → errors/side effects
```

If generated context conflicts with code, trust code and mark the generated node stale.

### Feature work

Start with:

```text
atlas/knowledge/cards/business-rule-cards.json
atlas/knowledge/cards/user-story-cards.json
atlas/knowledge/indexes/by_domain.yaml
atlas/context-packs/requirements-context.md
.kiro/steering/codeatlas-rules.md
```

Before implementing, identify:

- impacted business rules
- impacted technical rules
- existing validation/permission/error/state patterns
- frontend/backend contract expectations
- tests that should be updated

Preserve existing business behaviour unless the user explicitly asks to change it.

### Refactoring

Start with:

```text
atlas/knowledge/edges.yaml
atlas/knowledge/indexes/by_file.yaml
atlas/context-packs/refactoring-context.md
atlas/knowledge/audit/reverse-verification-report.md
```

Do not refactor across a rule boundary without checking business-rule and technical-rule impacts.

### Test generation

Start with:

```text
atlas/knowledge/nodes/user_stories.yaml
atlas/knowledge/nodes/acceptance_criteria.yaml
atlas/knowledge/nodes/business_rules.yaml
atlas/context-packs/testing-context.md
```

Generate tests from acceptance criteria, business rules, permission rules, validation rules, error handling, and state transitions.

### Merge-request review

Start with:

```text
docs/MERGE_REQUEST_REVIEW_FRAMEWORK.md
atlas/context-packs/mr-review-context.md
atlas/knowledge/indexes/by_file.yaml
atlas/knowledge/audit/reverse-verification-report.md
atlas/knowledge/audit/unsupported-claims.md
```

Draft comments first. Do not post comments unless explicit approval is present.

## Handling uncertainty

Respect these fields:

```text
confidence
needs_review
status
verification_status
```

If a node is low confidence or `needs_review: true`, do not treat it as authoritative.

If a node is `approved`, preserve its ID and review state unless the user approves a business meaning change.

## Source-code conflict rule

When source code and generated Atlas context disagree:

1. trust source code for current behaviour,
2. mark the Atlas node stale or unsupported,
3. update reverse-verification findings,
4. recommend a targeted rerun,
5. avoid silently rewriting business meaning.

## Targeted rerun rule

Prefer targeted reruns over full reruns:

| Issue | Preferred command |
|---|---|
| generated context not normalized | `./atlas/scripts/run-knowledge-normalizer.sh` |
| generated claims need validation | `./atlas/scripts/run-reverse-verification.sh` |
| context packs stale | `./atlas/scripts/run-context-refresh.sh` |
| all three after extraction | `./atlas/scripts/run-post-extraction-suite.sh` |
| MR review needed | `./atlas/scripts/run-mr-review.sh <iid>` |

## Do not do this

Kiro should not:

- paste giant YAML dumps into prompts
- ignore low confidence or `needs_review` flags
- invent business rules from naming alone
- treat frontend-only validation as backend enforcement
- treat backend-only endpoints as dead code without proof
- rerun the whole framework when targeted refresh is enough
- post MR comments without approval
