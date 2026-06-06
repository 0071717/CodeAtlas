# CodeAtlas Pipeline

`atlas/` contains the machine-readable CodeAtlas framework: configuration,
prompts, scripts, schemas, deterministic tooling, and generated artifact
folders.

## Canonical flow

CodeAtlas is now **deterministic-first**. Start every new target project with the
V2 runner, then add bounded Kiro/AI enrichment only after source/index/graph
artifacts exist.

```bash
python3 atlas/tools/codeatlas_v2_canonical.py doctor
python3 atlas/tools/codeatlas_v2_canonical.py all
```

The V2 run creates conservative, evidence-backed artifacts in this order:

```text
source snapshot
→ deterministic indexes
→ graph and flows
→ payload/error/fact/knowledge seed layers
→ validation and visualizer exports
```

Legacy prompt-first scripts remain available for controlled exploration, but they
are not the default first run.

## Important directories

```text
atlas/
  config/        # project config, extraction policy, schemas, ecosystem bindings
  prompts/       # bounded prompts for legacy/enrichment phases
  scripts/       # automation entrypoints
  tools/         # deterministic V2 tooling and exporters
  source/        # source manifests, file hashes, provenance snapshots
  index/         # deterministic file/symbol/endpoint/route/API/test/config indexes
  payloads/      # request/response contract seeds and unresolved payload work
  runtime/       # middleware, dependency, exception-handler, auth/config maps
  graph/         # nodes, edges, contract mappings, flow-ready relationships
  errors/        # explicit and unresolved error-flow indexes
  flows/         # API request and UI flow seeds
  facts/         # evidence-backed technical facts
  testing/       # test inventory and test-candidate artifacts
  knowledge/     # normalized graph/read-model artifacts for downstream tools
  audit/         # validation, preflight, promotion, and drift reports
  change/        # changed files, impacted nodes/edges, targeted rerun plans
  visualizer/    # graph and flow exports for ReGraph/Cytoscape-style tools
```

## Core commands

Preflight and canonical all-in-one run:

```bash
python3 atlas/tools/codeatlas_v2_canonical.py doctor
python3 atlas/tools/codeatlas_v2_canonical.py all
```

Individual deterministic stages:

```bash
python3 atlas/tools/codeatlas_v2_canonical.py snapshot
python3 atlas/tools/codeatlas_v2_canonical.py index
python3 atlas/tools/codeatlas_v2_canonical.py graph
python3 atlas/tools/codeatlas_v2_canonical.py semantic-layers
python3 atlas/tools/codeatlas_v2_canonical.py validate
python3 atlas/tools/codeatlas_v2_canonical.py visualizer-export
```

Compatibility wrappers:

```bash
bash atlas/scripts/run-pre-transfer-check.sh
bash atlas/scripts/run-framework-v2-suite.sh
```

Legacy Kiro/prompt-first scripts such as `run-auto.sh`, `run-pilot-auto.sh`, and
`run-foundation.sh` should be treated as enrichment or migration tools, not as
the canonical starting path.

## Evidence rules

1. Source code is authoritative.
2. Deterministic indexes and graph artifacts come before AI-derived claims.
3. Generated facts must carry evidence or `needs_review: true`.
4. Missing payloads, error mappings, and links should be emitted as unresolved
   findings instead of invented.
5. If generated Atlas artifacts conflict with source code, mark Atlas stale and
   rerun the affected deterministic stages.
