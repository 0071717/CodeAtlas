You are Atlas Forge performing a robustness audit of the CodeAtlas framework and generated YAML foundation.

Goal:
Assess whether the current CodeAtlas artifacts are complete, consistent, and suitable as a foundation for downstream tools such as visualizers, Playwright generation, sample data planning, PR impact analysis, code health scoring, and requirements derivation.

Read:
- README.md
- docs/CODE_MAP_FOUNDATION.md
- docs/TOOLING_ROADMAP.md
- docs/MAINTENANCE_STRATEGY.md
- docs/WORKFLOW.md
- atlas/config/extraction-policy.md
- atlas/map/*.yaml if present
- atlas/facts/technical-facts.yaml if present
- atlas/domains/*/*.yaml if present
- atlas/architecture-discovery/* if present
- .kiro/steering/*.md

Write:
- atlas/audit/framework-audit-report.md
- atlas/audit/yaml-foundation-scorecard.yaml
- atlas/audit/missing-map-coverage.yaml
- atlas/audit/tool-readiness-matrix.md
- atlas/audit/recommended-next-actions.md

Assess:
- whether map files exist and are valid YAML
- whether stable IDs are used consistently
- whether code references are granular enough
- whether backend flows are mapped router → service → helper/service → data-access/OpenSearch
- whether frontend flows are mapped route → page → component → hook/state → API client → backend endpoint
- whether validation, permission, error, and state maps are populated
- whether technical facts are derived from map evidence
- whether rules are traceable to facts/map/code references
- whether contradictions are first-class artifacts
- whether outputs are suitable for downstream tools
- whether maintenance and branch governance are sufficiently represented

Score each area 1-10:
- architecture discovery quality
- code map coverage
- evidence quality
- ID stability
- frontend/backend contract traceability
- technical fact quality
- business rule derivability
- test-generation readiness
- visualizer readiness
- PR-impact readiness
- release-governance readiness
- code-health readiness

Rules:
- Be critical.
- Do not assume completeness just because files exist.
- Identify blocking gaps before downstream tool building.
- Provide concrete next actions.
- Mark uncertain findings with `needs_review: true`.
