# React Stack Candidate Indexer Tool

This guide documents the focused React-stack indexer added for projects using:

```text
React Router DOM
TanStack Query
Material UI
```

## Command

```bash
python3 atlas/tools/react_stack_candidate_indexer.py
```

Runner:

```bash
bash atlas/scripts/run-react-stack-indexer.sh
```

## Purpose

The foundation suite gives general React/TypeScript candidates. This tool adds stack-specific candidate indexes so AI-assisted workers can operate on smaller, better slices.

## Outputs

```text
atlas/index/react-router-index.yaml
atlas/index/tanstack-query-index.yaml
atlas/index/material-ui-index.yaml
atlas/map/ui-state-candidates.yaml
atlas/audit/react-stack-indexer-report.yaml
```

## What it captures

### React Router DOM

```text
createBrowserRouter
createRoutesFromElements
RouterProvider
BrowserRouter
Routes
Route
useRoutes
Navigate
useNavigate
useParams
useSearchParams
Outlet
```

### TanStack Query

```text
useQuery
useMutation
useInfiniteQuery
queryClient.invalidateQueries
queryClient.setQueryData
queryClient.refetchQueries
isLoading / isPending / isFetching
isError / isSuccess / error / data
```

### Material UI

```text
TextField
Select
Autocomplete
Checkbox
RadioGroup
Button
IconButton
LoadingButton
Dialog
Drawer
Snackbar
Alert
DataGrid
Table
Tabs
Menu
FormControl
FormHelperText
```

## Confidence

This is a heuristic candidate indexer. Most findings are `confidence: medium` or `low` and `needs_review: true`. AI-assisted mapping should enrich and validate them against source evidence.

## Recommended sequence

```text
1. python3 atlas/tools/codeatlas_v2_suite.py all
2. python3 atlas/tools/react_stack_candidate_indexer.py
3. Run atlas/prompts/framework/10-react-stack-ui-mapper.md for one route/page cluster.
4. Run atlas/prompts/framework/13-ui-api-contract-mapper.md for the linked API client.
5. Run atlas/prompts/framework/14-playwright-from-ui-flow-worker.md after flow validation.
```
