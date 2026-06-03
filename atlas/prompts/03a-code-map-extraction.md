You are acting as a senior codebase cartographer.

Goal:
Build a granular semantic YAML map of the application. This map is the foundation for later technical facts, technical rules, business rules, PR impact analysis, code health analysis, test gap analysis, and release governance.

Do not create business rules yet.
Do not create user stories yet.
Do not summarize vaguely.

Read:
- atlas/config/project.yaml
- atlas/config/extraction-policy.md
- atlas/architecture-discovery/extraction-traversal-guide.md if present
- atlas/global/frontend-inventory.yaml
- atlas/global/backend-inventory.yaml
- atlas/global/domain-map.yaml

Write:
- atlas/map/repo-map.yaml
- atlas/map/domain-map.yaml
- atlas/map/code-references.yaml
- atlas/map/backend-map.yaml
- atlas/map/frontend-map.yaml
- atlas/map/api-map.yaml
- atlas/map/schema-map.yaml
- atlas/map/call-graph.yaml
- atlas/map/ui-flow-map.yaml
- atlas/map/data-access-map.yaml
- atlas/map/validation-map.yaml
- atlas/map/permission-map.yaml
- atlas/map/error-map.yaml
- atlas/map/state-map.yaml
- atlas/map/integration-map.yaml

Mapping principles:
1. Build a semantic map, not an AST dump.
2. Capture behaviourally meaningful structure.
3. Use stable IDs where possible.
4. Every major map item should include evidence: repo, file, symbol, and line range where available.
5. Do not include generated/vendor/cache folders unless relevant.
6. Mark confidence as high, medium, or low.
7. Mark uncertainty explicitly as `needs_review: true`.

Backend map requirements:
- map router files and registered routers
- map endpoints with method/path/handler
- map request/response Pydantic models
- map auth/permission dependencies
- map endpoint → service calls
- map service → service/helper calls
- map service → OS/OpenSearch/data-access calls
- map errors/exceptions/status codes
- map side effects
- map tests where obvious

For this API, assume the expected backend traversal pattern is often:

router endpoint
→ service function
→ helper/service function
→ OS/OpenSearch/data-access function such as `*_os.py`
→ response model/errors

Verify this pattern from code rather than blindly assuming it.

Frontend map requirements:
- map routes/pages
- map page → components
- map components → hooks/state
- map forms and validation schemas
- map API clients
- map frontend API call → backend endpoint
- map loading/error/success states
- map permission/feature-flag checks
- map tests where obvious

Cross-repo requirements:
- map frontend request types to backend Pydantic models where possible
- map frontend response types to backend response models where possible
- identify unmapped frontend API calls
- identify backend-only endpoints
- identify naming mismatches

Output format:
Write valid YAML files only for map outputs.
Use arrays and objects, not prose blobs.
Prose explanations can be added as YAML comments only if useful.
