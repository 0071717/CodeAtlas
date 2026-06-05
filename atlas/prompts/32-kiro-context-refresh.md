You are Memory Smith refreshing Kiro context from the normalized CodeAtlas knowledge layer.

Goal:
Make Kiro and future AI coding agents use the generated CodeAtlas maps, rules, requirements, and verification findings effectively without loading huge YAML dumps into every task.

Read in this order:
1. atlas/knowledge/manifest.yaml if present
2. atlas/knowledge/indexes/*.yaml if present
3. atlas/knowledge/cards/*.json if present
4. atlas/knowledge/audit/*.md if present
5. atlas/context-packs/*.md if present
6. atlas/knowledge/nodes/*.yaml if present
7. atlas/knowledge/edges.yaml if present
8. atlas/map/*.yaml, atlas/facts/*.yaml, atlas/domains/*/*.yaml as fallback
9. .kiro/steering/*.md if present

Write or update:
- atlas/context-packs/global-context.md
- atlas/context-packs/domain-<domain_id>-context.md where useful
- atlas/context-packs/debugging-context.md
- atlas/context-packs/testing-context.md
- atlas/context-packs/refactoring-context.md
- atlas/context-packs/mr-review-context.md
- atlas/context-packs/requirements-context.md
- .kiro/steering/codeatlas-context.md
- .kiro/steering/codeatlas-rules.md
- .kiro/steering/codeatlas-review-guidance.md
- .kiro/steering/codeatlas-debugging-guidance.md

Context pack rules:
- Keep files compact and useful.
- Do not paste full YAML dumps.
- Reference stable IDs from atlas/knowledge.
- Include the context priority order.
- Include where to look first for debugging, feature work, tests, refactors, and MR reviews.
- Preserve uncertainty markers, low confidence warnings, unsupported claims, and reverse-verification findings.
- Clearly distinguish generated candidate knowledge from approved knowledge.

Required steering guidance:
Kiro should use CodeAtlas context in this order when answering code questions:
1. Ask: which domain/files/rules are relevant?
2. Read atlas/knowledge/indexes to find related nodes quickly.
3. Read relevant cards for human-readable summaries.
4. Read relevant context packs.
5. Read relevant nodes/edges only as needed.
6. Read raw source code for implementation details or verification.
7. If generated Atlas context conflicts with source code, trust source code and flag the Atlas artifact as stale.

Kiro should not:
- assume generated rules are perfect
- ignore low-confidence or needs_review flags
- make business-rule changes without preserving traceability
- paste huge generated files into prompts
- rerun the whole framework when a targeted rerun is enough

Finish by writing a short report:
- atlas/context-packs/context-refresh-report.md

The report should list:
- files updated
- domains included
- high-priority unsupported claims
- stale context risks
- recommended next commands
