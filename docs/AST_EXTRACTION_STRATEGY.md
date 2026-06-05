# AST Extraction Strategy

CodeAtlas should use ASTs and deterministic parsing to build stable low-level indexes, but it should not store raw AST dumps as the main knowledge model.

## Rule

```text
Use parsers to see structure.
Use CodeAtlas YAML to represent useful knowledge.
Use AI only for bounded semantic enrichment.
```

## What deterministic extraction should capture

```text
files
hashes
line counts
functions
classes
React components/hooks candidates
FastAPI endpoints
Pydantic/BaseModel candidates
basic call names
routes
API client calls
test files
```

## What not to capture by default

```text
every local variable
every import unless architecturally relevant
every JSX element
every expression tree
vendor/generated/build artifacts
raw parser trees that are hard for Kiro to consume
```

## Python approach

Use `ast` first because it is standard-library and fast.

Capture:

```text
FunctionDef / AsyncFunctionDef / ClassDef
line_start / line_end
calls inside functions
FastAPI decorator candidates
raise statements in later versions
if-branch summaries in later versions
BaseModel schema candidates in later versions
```

Use `libcst` or richer tooling later only when exact formatting-preserving rewrites are needed.

## TypeScript/React approach

Start with fast regex/tree-sitter/TypeScript parser extraction.

Capture:

```text
function/class/const component candidates
use* hook candidates
<Route path=...> candidates
fetch/axios/client API calls
spec/test files
```

Later, replace regex with `ts-morph` or TypeScript compiler API for stronger type-aware extraction.

## Output rule

AST-derived output should be reduced into stable CodeAtlas artifacts:

```text
atlas/index/symbol-index.yaml
atlas/index/endpoint-index.yaml
atlas/index/route-index.yaml
atlas/index/api-client-index.yaml
atlas/index/test-index.yaml
```

These artifacts become inputs to map, graph, flow, fact, rule, testing, and visualization layers.
