You are Atlas Forge normalizing existing CodeAtlas outputs into a machine-readable Requirements Knowledge Base.

Important context:
The full Atlas framework may already have been run. Do not rerun the entire framework. Treat current generated outputs as a baseline candidate and normalize them.

Goal:
Create `atlas/knowledge/` as the primary machine-readable layer for AI context, future UI visualisation, merge-request review, rule maintenance, PR impact analysis, test planning, and targeted reruns.

Read:
- docs/KNOWLEDGE_CONTEXT_LAYER.md
- docs/YAML_CONTRACT.md
- docs/CODE_MAP_FOUNDATION.md
- docs/CODE_ATLAS_REVERSE_VERIFICATION.md
- atlas/architecture-discovery/* if present
- atlas/global/* if present
- atlas/map/*.yaml if present
- atlas/facts/*.yaml if present
- atlas/domains/*/*.yaml if present
- atlas/audit/* if present
- atlas/context-packs/*.md if present
- .kiro/steering/*.md if present

Write:
- atlas/knowledge/manifest.yaml
- atlas/knowledge/nodes/domains.yaml
- atlas/knowledge/nodes/code_refs.yaml
- atlas/knowledge/nodes/code_map_nodes.yaml
- atlas/knowledge/nodes/technical_facts.yaml
- atlas/knowledge/nodes/technical_rules.yaml
- atlas/knowledge/nodes/business_rules.yaml
- atlas/knowledge/nodes/user_stories.yaml
- atlas/knowledge/nodes/acceptance_criteria.yaml
- atlas/knowledge/nodes/epics.yaml
- atlas/knowledge/nodes/high_level_requirements.yaml
- atlas/knowledge/nodes/contradictions.yaml
- atlas/knowledge/nodes/dead_code_candidates.yaml
- atlas/knowledge/edges.yaml
- atlas/knowledge/indexes/by_domain.yaml
- atlas/knowledge/indexes/by_file.yaml
- atlas/knowledge/indexes/by_code_ref.yaml
- atlas/knowledge/indexes/by_requirement.yaml
- atlas/knowledge/indexes/by_business_rule.yaml
- atlas/knowledge/indexes/by_user_story.yaml
- atlas/knowledge/graph/requirements-graph.json
- atlas/knowledge/graph/cytoscape-elements.json
- atlas/knowledge/graph/force-graph.json
- atlas/knowledge/graph/mermaid-summary.mmd
- atlas/knowledge/cards/business-rule-cards.json
- atlas/knowledge/cards/user-story-cards.json
- atlas/knowledge/cards/requirement-cards.json
- atlas/knowledge/cards/domain-cards.json
- atlas/knowledge/audit/evidence-chain-audit.md
- atlas/knowledge/audit/orphan-node-report.md
- atlas/knowledge/audit/unsupported-claims.md
- atlas/knowledge/audit/confidence-report.md
- atlas/knowledge/audit/contradiction-report.md

Canonical node requirements:
Every node must have, where possible:
- id
- type
- domain where applicable
- name
- summary
- statement or description
- status: candidate | reviewed | approved | deprecated
- confidence: high | medium | low
- needs_review: true | false
- source_artifacts
- evidence
- derived_from where applicable
- related_nodes where useful
- ui metadata where useful
- ai metadata where useful

Traceability rules:
- Every technical fact must have map/code evidence.
- Every technical rule must derive from technical facts or direct code/map evidence.
- Every business rule must derive from technical rules.
- Every user story must derive from business rules.
- Every acceptance criterion must derive from a business rule, technical rule, or user story.
- Every epic must derive from user stories.
- Every high-level requirement must derive from epics.
- If any chain is broken, do not invent missing evidence. Mark `needs_review: true`, lower confidence, and list it in `unsupported-claims.md`.

Machine output rules:
- Export nodes and edges separately.
- Build graph JSON suitable for a future React/Cytoscape/force-graph UI.
- Build cards JSON suitable for detail panels.
- Build indexes so agents can quickly find relevant context by domain, file, rule, story, and requirement.
- Keep Markdown reports concise and human-readable.

AI context rules:
- Add `ai.context_priority` to important nodes.
- Add `ai.update_policy` guidance where useful.
- Do not paste full YAML dumps into context packs.
- Preserve stable IDs and review state.

Do not:
- Rerun the full Atlas framework.
- Overwrite original domain outputs.
- Invent requirements.
- Treat frontend-only validation as backend enforcement.
- Treat backend-only endpoints as dead code without evidence.

Finish by writing `atlas/knowledge/README.md` explaining how Kiro, future UIs, and review tools should consume this layer.
