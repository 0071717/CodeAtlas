You are Atlas Forge building a CodeAtlas code health analyzer.

Goal:
Use the granular YAML Code Map to identify architecture drift, inconsistent patterns, risky hotspots, test gaps, contract issues, and refactor opportunities.

Read:
- docs/CODE_MAP_FOUNDATION.md
- atlas/map/*.yaml
- atlas/facts/technical-facts.yaml
- atlas/domains/*/*.yaml where available
- atlas/architecture-discovery/extraction-traversal-guide.md

Write:
- atlas/code-health/architecture-violations.yaml
- atlas/code-health/domain-health-scores.yaml
- atlas/code-health/risk-hotspots.yaml
- atlas/code-health/refactor-roadmap.md
- atlas/code-health/test-gap-report.md
- atlas/code-health/README.md

Analyze:
- routers with business logic or direct data-access/OpenSearch calls
- services with too many responsibilities
- cross-domain service coupling
- frontend/backend contract mismatches
- frontend-only business validation
- backend-only behaviour with poor UI support
- permissions enforced only in frontend
- endpoints without frontend callers
- frontend API calls without backend endpoints
- rules/facts without test evidence
- duplicated or inconsistent validation
- large/high-fan-in/fan-out functions or domains

Scoring:
For each domain, score 1-10:
- router thinness
- service cohesion
- data-access separation
- contract consistency
- validation consistency
- permission consistency
- test evidence
- dead-code risk
- overall maintainability

Rules:
- Use YAML evidence first.
- Do not invent issues unsupported by map/fact evidence.
- Mark uncertain findings as `needs_review: true`.
- Separate safe cleanup from risky refactors.
- Provide practical refactor recommendations.
