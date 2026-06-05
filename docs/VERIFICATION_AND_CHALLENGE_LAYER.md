# Verification and Challenge Layer

CodeAtlas outputs are claims. Claims must be checked.

The verification layer exists to prevent generated YAML from becoming stale documentation with extra structure.

## Verification stages

```text
1. parse/schema validation
2. ID/link validation
3. source evidence validation
4. contract validation
5. flow validation
6. cross-artifact consistency validation
7. adversarial challenge review
8. human approval for business meaning changes
```

## Deterministic checks

```text
files still exist
file hashes match or drift is reported
symbols still exist where possible
edge source and target IDs exist
flow steps reference valid nodes
evidence points to real files
frontend API clients match backend method/path where possible
```

## Challenge review statuses

Adversarial AI review should use only these statuses:

```text
SUPPORTED
PARTIALLY_SUPPORTED
UNSUPPORTED
CONTRADICTED
INSUFFICIENT_EVIDENCE
```

## Challenge prompt rule

The challenge reviewer must not repair claims. It should classify support, give a short reason, identify missing evidence, and recommend the smallest targeted rerun.

## Confidence handling

```yaml
confidence: low
needs_review: true
verification_status: unsupported_claim
```

Use this when a claim cannot be verified.

```yaml
confidence: medium
needs_review: true
verification_status: partially_verified
```

Use this when evidence exists but is incomplete.

```yaml
confidence: high
needs_review: false
verification_status: verified
```

Use this only when evidence directly supports the claim.

## Source conflict rule

If source code conflicts with Atlas, source code wins. Mark the Atlas node, edge, flow, fact, rule, or requirement as stale, unsupported, or contradicted.
