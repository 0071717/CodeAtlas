# CodeAtlas Reverse Verification

Reverse verification is the accuracy safety net for CodeAtlas.

Normal extraction flows from source code into maps, facts, rules, stories, and requirements. Reverse verification checks the generated artifacts back against source evidence:

```text
source code
→ generated Atlas artifacts
→ reverse check against source code and evidence chain
```

## Why this exists

Generated maps and requirements can become wrong because:

- the extractor misunderstood a code path
- code changed after extraction
- line ranges moved
- a symbol was renamed
- a business rule was inferred too aggressively
- frontend and backend behaviour diverged
- generated YAML has broken links or orphaned IDs

Reverse verification improves accuracy by treating generated artifacts as claims that must be checked against evidence.

## What reverse verification checks

Reverse verification should inspect generated artifacts and validate:

1. referenced files still exist
2. referenced symbols still exist where possible
3. referenced line ranges still contain related behaviour where possible
4. Code Map nodes have usable evidence
5. technical facts derive from map/code evidence
6. technical rules derive from facts or direct evidence
7. business rules derive from technical rules
8. user stories derive from business rules
9. acceptance criteria derive from rules or stories
10. frontend API clients still match backend endpoints and schemas
11. permission, validation, error, state, and side-effect claims are evidenced
12. contradictions are first-class findings
13. backend-only endpoints are not treated as dead without proof
14. stale generated claims are marked `needs_review: true`

## Outputs

Reverse verification writes:

```text
atlas/knowledge/audit/reverse-verification-report.md
atlas/knowledge/audit/stale-map-candidates.yaml
atlas/knowledge/audit/invalid-evidence.yaml
atlas/knowledge/audit/claim-to-code-checks.yaml
atlas/knowledge/audit/targeted-rerun-plan.md
```

## Finding categories

Use these categories consistently:

```text
verified
partially_verified
unsupported_claim
stale_evidence
missing_code_reference
broken_traceability
frontend_backend_mismatch
possible_dead_code
needs_human_review
```

## Confidence handling

Reverse verification must not silently fix unsupported claims.

If a claim cannot be verified:

```yaml
confidence: low
needs_review: true
verification_status: unsupported_claim
```

If evidence is present but incomplete:

```yaml
confidence: medium
needs_review: true
verification_status: partially_verified
```

If evidence directly supports the claim:

```yaml
confidence: high
needs_review: false
verification_status: verified
```

## Targeted rerun policy

Reverse verification should recommend targeted reruns instead of full regeneration whenever possible:

| Problem | Preferred action |
|---|---|
| bad or stale line evidence | rerun code reference extraction |
| shallow map for one domain | rerun map/facts for that domain |
| weak technical facts | rerun fact extraction |
| invented business rules | rerun business-rule derivation from technical rules |
| weak user stories | rerun story/epic/HLR derivation |
| contract mismatch | rerun API/schema/contract mapping and contradiction scan |
| many global architecture errors | rerun architecture discovery and map foundation |

## Human review rule

Reverse verification can mark issues, suggest reruns, and prepare patches, but it must not approve business meaning changes by itself.

Meaningful changes to approved business rules, user stories, epics, or high-level requirements require human approval.
