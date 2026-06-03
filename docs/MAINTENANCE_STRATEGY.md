# CodeAtlas Maintenance Strategy

CodeAtlas should be maintained as a living requirements baseline, not a one-time documentation dump.

The goal is to keep extracted rules aligned with ongoing development across `develop/*`, `release/*`, and production branches.

## Core model

```text
Code change
→ impacted files
→ impacted domains
→ targeted re-extraction
→ rule delta
→ contradiction/regression scan
→ PR/release report
→ human approval for meaningful requirement changes
→ baseline update
```

Do not regenerate the entire requirements corpus on every pull request. Use targeted, diff-based maintenance.

## Branch strategy

| Branch type | Meaning | CodeAtlas behaviour |
|---|---|---|
| `develop/*` | future release work | advisory + moderate checks |
| `release/*` | release candidate | strict baseline checks |
| `main` / production | shipped behaviour | strictest drift checks |

## Pull request workflow

For every app PR:

1. Detect changed files.
2. Map changed files to CodeAtlas domains.
3. Re-run extraction only for impacted domains.
4. Compare newly extracted rules to the current baseline.
5. Classify added, modified, removed, contradicted, or unchanged rules.
6. Post a PR impact report.
7. Block only high-risk issues by default.

## Rule delta classifications

| Type | Meaning | Default action |
|---|---|---|
| `no_rule_impact` | code changed, behaviour unchanged | pass |
| `technical_rule_modified` | implementation-level behaviour changed | developer review |
| `business_rule_modified` | business behaviour changed | product owner review |
| `rule_added` | new behaviour detected | review and approve |
| `rule_removed` | previous behaviour deleted | review and approve |
| `contradiction` | frontend/backend or code/rule mismatch | fix or explicitly accept |
| `regression` | approved rule appears violated | block |
| `unknown` | Kiro is uncertain | human review |

## Blocking policy

### PRs to `develop/*`

Block only:

- critical authorization/security mismatch
- frontend/backend API contract break
- invalid generated artifacts
- broken extraction validation

Warn on:

- new business rules
- changed business rules
- dead-code candidates
- low-confidence extraction findings

### PRs to `release/*`

Block:

- unapproved business rule changes
- high/critical contradictions
- API contract mismatches
- deleted approved rules
- release-baseline drift

### PRs to `main`

Block:

- any mismatch from the approved release baseline
- any unapproved requirement delta
- any high/critical contradiction

## Human approval rules

| Change | Reviewer |
|---|---|
| technical rule wording | developer |
| API contract change | frontend/backend owner |
| business rule change | product owner |
| user story change | product owner |
| high-level requirement change | product/leadership |
| auth/security change | tech lead/security reviewer |
| release-branch behaviour change | release owner |

## Release freeze

When a release branch is cut, CodeAtlas should snapshot the approved baseline:

```text
atlas/releases/<release>/
  requirements-baseline.json
  domain-map.yaml
  contradiction-index.yaml
  approved-rules.yaml
  release-requirement-impact.md
```

Bugfix PRs into release branches should be checked against this frozen baseline.

## Scheduled drift checks

Run a full drift check weekly or before major release milestones:

```text
current code
vs
approved CodeAtlas baseline
```

The drift check should identify:

- rules no longer evidenced by code
- new behaviours not represented in rules
- stale `.kiro/steering` guidance
- dead-code candidates
- frontend/backend contract drift

## Recommended command set

Future CodeAtlas commands should support:

```bash
codeatlas pr-impact --base develop --head feature/foo
codeatlas rule-delta --domain knowledge_management
codeatlas release-freeze --release 2026.07
codeatlas drift-check --branch develop
```
