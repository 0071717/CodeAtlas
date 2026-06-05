# Testing Archaeology

Existing tests are evidence, even when they are weak.

CodeAtlas should inventory and classify existing tests before generating new ones. Poor tests still reveal fixtures, auth setup, mocks, historical behaviours, test data patterns, and missing coverage.

## Artifacts

```text
atlas/testing/test-inventory.yaml
atlas/testing/python-test-map.yaml
atlas/testing/fixture-map.yaml
atlas/testing/mock-map.yaml
atlas/testing/test-quality-report.yaml
atlas/testing/coverage-gaps.yaml
```

## What to capture

```text
test files
test functions/spec names
fixtures used
mocked services/data stores
API/client setup
auth setup
sample data factories
assertion strength
covered endpoints/routes/flows
missing validation/error/permission branches
```

## Quality classification

```yaml
quality:
  assertion_strength: weak | medium | strong
  covers_success_path: true
  covers_validation_errors: false
  covers_permission_errors: false
  covers_side_effects: false
  uses_mocks: true
  flaky_risk: medium
  improvement_suggestion: Add assertions for persistence and error branch.
```

## Kiro rule

Do not discard weak tests. Map them, classify them, then generate improvement candidates and gap reports.

A future test generator should prefer improving existing project patterns before inventing a new test style.
