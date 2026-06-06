# Legacy and Experimental Paths

This document prevents Kiro from confusing older prompt-first workflows with the canonical V2 deterministic path.

## Canonical path

Use the V2 deterministic tools first:

```bash
python3 atlas/tools/codeatlas_v2_canonical.py doctor
python3 atlas/tools/codeatlas_v2_canonical.py all
```

Then use targeted enrichment prompts and reverse verification.

## Legacy / exploratory path

The following scripts and prompts come from the older architecture-discovery and prompt-orchestration workflow:

```text
bash atlas/scripts/run-auto.sh
bash atlas/scripts/run-pilot-auto.sh
bash atlas/scripts/run-foundation.sh
atlas/scripts/run-architecture-discovery.sh
atlas/scripts/run-global.sh
atlas/scripts/run-code-map.sh
atlas/scripts/orchestrate_extraction.py
atlas/prompts/00-*.md through older extraction/domain prompts
```

These are not deleted because they contain useful process knowledge. However, Kiro should treat them as legacy/experimental unless the user explicitly asks to run the old pipeline.

## Safe use of legacy prompts

Legacy prompts may be used for:

```text
human-readable discovery
exploratory domain slicing
AI-assisted summaries
context-pack drafting
framework comparison
```

Legacy prompts should not be used as the first source of truth for:

```text
endpoint inventory
route inventory
query DSL reconstruction
permission enforcement
error flows
coverage claims
business rules
requirements
```

## Promotion rule

A legacy or AI-derived output can only be promoted to canonical knowledge when:

```text
it references deterministic Atlas IDs
it cites evidence
it passes validation
it survives adversarial challenge where appropriate
it preserves confidence and needs_review fields
```
