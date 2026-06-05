# AI-Assisted Extraction Strategy

CodeAtlas should be deterministic-first, but it should not be deterministic-only.

For mature codebases, AI-assisted passes are useful when building a perfect parser would be slower than a bounded, evidence-driven review of targeted files.

## Principle

```text
Deterministic tools create the index and evidence boundaries.
AI-assisted workers enrich only bounded slices.
Validators challenge the result.
```

AI should not read the whole repo and invent a model. It should read:

```text
1. the relevant index artifacts
2. a small set of source files selected by the index
3. the relevant layer contract
4. the output schema or expected YAML shape
```

## When AI-assisted extraction is appropriate

Use AI-assisted extraction for:

```text
React component responsibility summaries
TanStack Query hook behaviour
React Router flow interpretation
Material UI form/action/state interpretation
FastAPI dependency/middleware meaning
service-layer branch summaries
error/permission/validation extraction
UI state mapping
API request flow branch summaries
existing test quality review
business-rule and test-candidate wording
```

Use deterministic extraction for:

```text
file hashes
line counts
file classification
symbol discovery
endpoint candidates
route candidates
API client candidates
test file candidates
link validation
changed-file drift detection
```

## AI evidence rule

Every AI-created item must include one of:

```yaml
evidence:
  - type: code
    repo: frontend
    file: src/features/claims/ClaimForm.tsx
    symbol: ClaimForm
    line_start: 1
    line_end: 180
```

or:

```yaml
confidence: low
needs_review: true
verification_status: insufficient_evidence
```

## Bounded source policy

AI workers should operate on bounded slices:

```text
one route/page at a time
one backend endpoint at a time
one form/action flow at a time
one service function plus direct callees
one domain folder at a time
one test file or fixture cluster at a time
```

Do not ask AI to map the entire frontend or backend in a single pass.

## Recommended AI-assisted pass order

```text
1. deterministic snapshot/index
2. route/endpoint candidate discovery
3. AI route/page enrichment
4. AI form/action/query enrichment
5. AI backend endpoint/service enrichment
6. AI UI-to-API contract review
7. AI flow branch/state review
8. deterministic link/source validation
9. adversarial challenge review
10. targeted rerun plan
```

## Output discipline

AI-assisted workers must write structured artifacts, not narrative-only notes.

Good:

```text
atlas/map/component-map.yaml
atlas/map/form-map.yaml
atlas/map/ui-state-map.yaml
atlas/flows/ui-flows.yaml
atlas/flows/api-request-flows.yaml
atlas/audit/adversarial-review.yaml
```

Bad:

```text
random markdown summaries with no IDs, evidence, confidence, or rerun guidance
```

## Verification rule

AI-assisted findings are never automatically authoritative. They become trustworthy only after:

```text
schema/link validation passes
source evidence exists
confidence is appropriate
adversarial review does not contradict them
stale/drift checks are clean
```
