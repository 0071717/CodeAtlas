# Kiro Changelog — V2 React Stack Indexer

## 2026-06-05 — React Router, TanStack Query, and Material UI candidate indexer

### Added tool

- `atlas/tools/react_stack_candidate_indexer.py`
  - Plain Python heuristic indexer for frontend repos using React Router DOM, TanStack Query, and Material UI.
  - Produces stack-specific candidate artifacts for bounded AI-assisted mapping.

### Added runner

- `atlas/scripts/run-react-stack-indexer.sh`

### Added docs

- `docs/REACT_STACK_INDEXER_TOOL.md`
  - Documents command, outputs, stack-specific targets, confidence policy, and recommended sequence.

### Outputs

```text
atlas/index/react-router-index.yaml
atlas/index/tanstack-query-index.yaml
atlas/index/material-ui-index.yaml
atlas/map/ui-state-candidates.yaml
atlas/audit/react-stack-indexer-report.yaml
```

### Recommended use

Run after the V2 foundation suite:

```bash
python3 atlas/tools/codeatlas_v2_suite.py all
python3 atlas/tools/react_stack_candidate_indexer.py
```

Then run the React stack UI mapper prompt on one route/page cluster.
