# Targeted Rerun Engine

CodeAtlas should not regenerate the whole knowledge base on every merge request.

The targeted rerun engine maps code/config changes to the smallest affected Atlas layers.

## Change chain

```text
changed file
→ changed symbol or config item
→ impacted index node
→ impacted map node
→ impacted graph edge
→ impacted flow
→ impacted fact/rule/requirement
→ impacted tests/tools/context packs
→ targeted rerun plan
```

## Artifacts

```text
atlas/change/changed-files.yaml
atlas/change/changed-symbols.yaml
atlas/change/impacted-nodes.yaml
atlas/change/impacted-flows.yaml
atlas/change/impacted-rules.yaml
atlas/change/impacted-tests.yaml
atlas/change/targeted-rerun-plan.yaml
atlas/change/pr-impact-report.md
```

## File-type defaults

```text
Python source changed
→ rerun index, backend maps, graph, api flows, facts, tests.

React/TypeScript source changed
→ rerun index, frontend maps, graph, ui flows, tests.

Config/schema/search file changed
→ rerun config map, contracts, graph, affected flows.

Test file changed
→ rerun test inventory, coverage graph, test gap analysis.
```

## Merge request policy

For every merge request:

```text
1. detect changed files
2. compare file hashes
3. map changes to impacted nodes
4. produce targeted rerun plan
5. rerun only affected layers
6. compare old vs new facts/rules/flows
7. produce PR impact report
```

## Safety rule

If the impacted area cannot be determined, mark the result `unknown` and recommend a broader rerun. Do not pretend the change has no impact.
