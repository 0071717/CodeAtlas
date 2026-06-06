# Pre-Transfer Readiness Checklist

Use this checklist before copying CodeAtlas into the restricted Kiro network.

## Must be clear before transfer

- [ ] `docs/CANONICAL_EXECUTION_PATH.md` says the V2 deterministic path is canonical.
- [ ] `docs/LEGACY_AND_EXPERIMENTAL_PATHS.md` warns Kiro not to default to the old prompt-first pipeline.
- [ ] `docs/KIRO_ZIP_HANDOFF.md` points Kiro to the V2 docs.
- [ ] `docs/GRAPHIFY_PATTERNS_ADOPTED.md` explains graph/report/query helpers as derived read models.
- [ ] `docs/REPO_CLEANUP_AUDIT.md` separates canonical, legacy, future, and generated-output paths.
- [ ] `atlas/config/project.yaml` has been edited for the target workspace or is clearly still a template.
- [ ] `atlas/config/project.schema.json` exists.
- [ ] `atlas/config/ecosystem-bindings.yaml` includes ngk, FastAPI/React stack, Leaflet, ReGraph, TanStack Query, Material UI, and OpenSearch bindings.
- [ ] `atlas/tools/codeatlas_v2_suite.py` exists and is readable plain Python.
- [ ] `atlas/tools/codeatlas_v2_canonical.py` exists.
- [ ] `atlas/tools/validate_artifacts.py` exists.
- [ ] `atlas/tools/codeatlas_graph_report.py` exists.
- [ ] `atlas/tools/codeatlas_graph_html.py` exists.
- [ ] `atlas/tools/ngk_trace_regraph_exporter.py` exists.
- [ ] `atlas/tools/codeatlas_preflight_doctor.py` exists.
- [ ] `atlas/scripts/run-pre-transfer-check.sh` exists.
- [ ] No required first-run command depends on MCP.
- [ ] No required first-run command depends on external network access.

## Recommended local check

Run from the CodeAtlas repo root:

```bash
bash atlas/scripts/run-pre-transfer-check.sh
```

If target repos are available locally, also run:

```bash
bash atlas/scripts/run-framework-v2-suite.sh
python3 atlas/tools/ngk_trace_regraph_exporter.py "POST /example" || true
```

The placeholder trace may fail if no endpoint matches `POST /example`; that is acceptable. The goal is clean failure and valid helper output.

Review:

```text
atlas/audit/preflight-doctor-report.json
atlas/audit/artifact-json-promotion-report.json
atlas/audit/artifact-validation-report.json
atlas/visualizer/GRAPH_REPORT.md
atlas/visualizer/graph.json
atlas/visualizer/graph.html
```

## Transfer package should include

```text
README.md
docs/
atlas/config/
atlas/tools/
atlas/scripts/
atlas/prompts/
.kiro/agents/
```

Generated artifacts are optional. If generated artifacts are included, Kiro must validate them before trusting them.

## Do not transfer generated private artifacts by accident

Generated Atlas artifacts can contain proprietary target-code knowledge. Keep them out of Git and out of transfer packages unless intentionally reviewed:

```text
atlas/source/
atlas/index/
atlas/payloads/
atlas/runtime/
atlas/graph/
atlas/flows/
atlas/audit/
atlas/change/
atlas/visualizer/
atlas/knowledge/
atlas/logs/
atlas/runs/
```

## Known intentional limitations before transfer

These are expected and should not surprise Kiro:

```text
The V2 deterministic suite is a foundation, not a complete parser suite.
TypeScript extraction still needs a real ts-morph/tree-sitter implementation.
FastAPI router/dependency materialisation still needs deeper implementation.
OpenSearch Query DSL reconstruction is specified but not fully implemented.
Error-flow extraction is specified but not fully implemented.
SQLite/DuckDB/Kuzu read models are planned but not yet canonical.
```

## Do not run first

Do not run these as the first action in the transferred workspace unless the user explicitly chooses the legacy pipeline:

```text
bash atlas/scripts/run-auto.sh
bash atlas/scripts/run-pilot-auto.sh
bash atlas/scripts/run-foundation.sh
```

Use the V2 deterministic path first.
