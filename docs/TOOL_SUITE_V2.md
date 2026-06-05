# CodeAtlas V2 Deterministic Tool Suite

This guide describes the first deterministic tools added for CodeAtlas V2.

The current suite is intentionally small and fast. It creates the foundation Kiro can inspect and improve:

```text
source snapshot
file hash index
file index
symbol index
endpoint index
route index
API client index
test index
graph nodes/edges
seed API request flows
validation report
drift report
visualizer JSON export
```

## Commands

Run all foundation steps:

```bash
python3 atlas/tools/codeatlas_v2_suite.py all
```

Or run individual steps:

```bash
python3 atlas/tools/codeatlas_v2_suite.py init
python3 atlas/tools/codeatlas_v2_suite.py snapshot
python3 atlas/tools/codeatlas_v2_suite.py index
python3 atlas/tools/codeatlas_v2_suite.py graph
python3 atlas/tools/codeatlas_v2_suite.py validate
python3 atlas/tools/codeatlas_v2_suite.py drift-check
python3 atlas/tools/codeatlas_v2_suite.py visualizer-export
```

Runner:

```bash
bash atlas/scripts/run-framework-v2-suite.sh
```

## Important implementation note

The suite is plain Python source in:

```text
atlas/tools/codeatlas_v2_suite.py
```

Do not reintroduce encoded/base64 payload launchers. Kiro and humans must be able to read, modify, review, and test the tool directly.

## Current limitations

The V2 suite is a foundation, not the full framework. It currently provides shallow deterministic extraction and graph seeds. Future bounded tasks should add:

```text
stronger TypeScript/React parser
Pydantic schema extractor
FastAPI middleware/dependency extractor
branch-aware API flow builder
UI state/interaction flow builder
OpenSearch/config extractor
fixture/mock/test archaeology extractor
contract checker
impact-to-targeted-rerun planner
```

## Output format

The files use JSON syntax with `.yaml` extensions for now. JSON is valid YAML and easier to parse with Python standard library. A later task may switch to a YAML library if desired, but deterministic parsability matters more than formatting.
