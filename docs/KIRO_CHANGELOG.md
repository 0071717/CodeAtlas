# Kiro Changelog

This changelog is written for Kiro, future AI agents, and humans maintaining CodeAtlas.

## 2026-06-05 — Knowledge context, reverse verification, and MR review framework

### Summary

CodeAtlas now has a stronger post-extraction workflow for turning generated maps/rules/requirements into a normalized machine-readable knowledge layer, verifying generated claims back against code, refreshing Kiro context, and preparing safe GitLab merge-request reviews.

### Added

- `docs/KNOWLEDGE_CONTEXT_LAYER.md`
  - Defines `atlas/knowledge/` as the normalized machine-readable layer above generated Atlas outputs.
  - Defines canonical node, edge, index, graph, card, and audit structures.
  - Defines AI context priority for Kiro and future agents.

- `docs/CODE_ATLAS_REVERSE_VERIFICATION.md`
  - Defines Code ↔ Atlas reverse verification.
  - Checks generated maps, facts, rules, stories, and requirements back against source evidence.
  - Adds stale evidence, unsupported claim, invalid evidence, and targeted rerun concepts.

- `docs/MERGE_REQUEST_REVIEW_FRAMEWORK.md`
  - Defines GitLab merge-request review workflow using `glab`.
  - Defaults to draft-only review.
  - Requires explicit approval before posting comments.
  - Requires all AI-generated comments to start with `✦ AI GENERATED REVIEW`.
  - Prefers inline comments where line context exists.

- `docs/KIRO_CONTEXT_USAGE.md`
  - Explains how Kiro should use `atlas/knowledge`, context packs, steering files, generated YAML, and source code.
  - Defines context priority and task-specific guidance for debugging, feature work, refactoring, tests, and MR reviews.

- `atlas/prompts/30-knowledge-normalizer.md`
  - Kiro prompt to normalize existing generated Atlas outputs into `atlas/knowledge/`.

- `atlas/prompts/31-reverse-verification.md`
  - Kiro prompt to verify generated Atlas claims back against code and traceability evidence.

- `atlas/prompts/32-kiro-context-refresh.md`
  - Kiro prompt to refresh context packs and `.kiro/steering` from normalized knowledge.

- `atlas/prompts/33-merge-request-review.md`
  - Kiro prompt for safe GitLab MR review using CodeAtlas context.

- `atlas/scripts/run-knowledge-normalizer.sh`
  - Runs prompt 30.

- `atlas/scripts/run-reverse-verification.sh`
  - Runs prompt 31.

- `atlas/scripts/run-context-refresh.sh`
  - Runs prompt 32.

- `atlas/scripts/run-mr-review.sh`
  - Runs prompt 33 for a GitLab MR IID.
  - Defaults to no comment posting.

- `atlas/scripts/run-post-extraction-suite.sh`
  - Runs normalization, reverse verification, and context refresh in sequence.

### Updated agents

- `.kiro/agents/atlas-forge.json`
  - Now prefers `atlas/knowledge` first.
  - Includes MR review safety guidance.

- `.kiro/agents/atlas-cartographer.json`
  - Now checks knowledge indexes, reverse-verification findings, stale-map candidates, and unsupported claims before map/fact changes.

- `.kiro/agents/domain-scout.json`
  - Now uses domain-relevant knowledge nodes, cards, edges, and reverse-verification findings before domain extraction/refresh.

- `.kiro/agents/rift-hunter.json`
  - Now explicitly handles reverse verification, unsupported claims, and stale generated artifacts.

- `.kiro/agents/memory-smith.json`
  - Now refreshes context packs and steering files from `atlas/knowledge`.

### Important behaviour changes

Kiro should now prefer this context order:

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

If source code and generated Atlas context disagree, Kiro should trust source code and mark the generated Atlas artifact stale or unsupported.

### Recommended next command in an existing workspace

After pulling these framework changes into a workspace that already has generated Atlas artifacts:

```bash
bash atlas/scripts/run-post-extraction-suite.sh
```

This should:

1. normalize generated outputs into `atlas/knowledge/`,
2. reverse-check generated claims against code evidence,
3. refresh Kiro context packs and `.kiro/steering` files.

### Note about executable bits

Files created through GitHub's contents API may not retain executable permissions. If running scripts with `./atlas/scripts/...` fails, run:

```bash
chmod +x atlas/scripts/*.sh
```

or invoke scripts with `bash atlas/scripts/<script>.sh`.
