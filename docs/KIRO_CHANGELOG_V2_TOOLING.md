# Kiro Changelog Addendum — V2 Tooling Improvements

This addendum records the latest deterministic tooling improvements for Kiro.

## 2026-06-05 — Improved readable Python V2 suite

### Changed

- `atlas/tools/codeatlas_v2_suite.py` was expanded as readable Python source.
- The suite now uses deterministic file scanning, hashing, AST parsing, graph building, flow seeding, drift reporting, validation, and visualizer export.
- Encoded payload launchers are no longer part of the active suite.

### New or improved outputs

```text
atlas/source/snapshot.yaml
atlas/source/file-hashes.yaml
atlas/index/file-index.yaml
atlas/index/symbol-index.yaml
atlas/index/import-index.yaml
atlas/index/endpoint-index.yaml
atlas/index/route-index.yaml
atlas/index/component-index.yaml
atlas/index/hook-index.yaml
atlas/index/api-client-index.yaml
atlas/index/schema-index.yaml
atlas/index/service-index.yaml
atlas/index/data-access-index.yaml
atlas/index/runtime-entrypoint-index.yaml
atlas/index/ui-action-index.yaml
atlas/index/test-index.yaml
atlas/index/config-index.yaml
atlas/runtime/runtime-map.yaml
atlas/testing/test-inventory.yaml
atlas/graph/nodes.yaml
atlas/graph/edges.yaml
atlas/flows/api-request-flows.yaml
atlas/flows/ui-flows.yaml
atlas/audit/v2-validation-report.yaml
atlas/change/changed-files.yaml
atlas/change/impacted-nodes.yaml
atlas/change/impacted-edges.yaml
atlas/change/targeted-rerun-plan.yaml
atlas/visualizer/graph-data.json
atlas/visualizer/cytoscape-elements.json
atlas/visualizer/node-detail-index.json
atlas/visualizer/flow-cards.json
```

### What Kiro should do next

Run:

```bash
python3 atlas/tools/codeatlas_v2_suite.py all
```

Then inspect:

```text
atlas/audit/v2-validation-report.yaml
atlas/source/snapshot.yaml
atlas/index/
atlas/graph/
atlas/flows/
atlas/visualizer/
```

### Known limitations

- TypeScript/React extraction is still regex-based and should later use a real parser.
- FastAPI router prefix handling is not complete.
- API flow branches are seeded from AST if-statements but not yet full symbolic execution.
- UI flows are route/API-call seeds, not complete state machines yet.
- OpenSearch/config extraction is only file/config indexing so far.
