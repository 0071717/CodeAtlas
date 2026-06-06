# React Stack Mapping Guide

This guide tells Kiro and CodeAtlas tools how to map the target React/TypeScript UI stack.

The expected UI libraries include:

```text
React Router DOM
TanStack Query
Material UI
Leaflet / react-leaflet
ReGraph
```

## Extraction strategy

Use deterministic candidate extraction first, then targeted AI-assisted enrichment.

```text
candidate extraction:
  imports, route declarations, query/mutation hooks, API client calls, actions, forms, library component usage

enrichment:
  route ownership, user journey, UI state meaning, query/mutation meaning, visual component semantics, test candidates
```

Regex is acceptable for early candidate discovery. It is not canonical for final React Router, TanStack Query, or UI flow mapping. Long term, use a TypeScript AST extractor such as ts-morph or tree-sitter.

## React Router DOM

Capture:

```text
<Route path=...>
createBrowserRouter route objects
useRoutes route objects
useNavigate calls
Navigate components
useParams usage
route guards/layouts
nested routes and outlets
```

Outputs:

```text
atlas/index/react-router-index.json
atlas/index/route-index.json
atlas/map/route-map.json
atlas/flows/ui-flows.json
```

## TanStack Query

Capture:

```text
useQuery
useMutation
useInfiniteQuery
useQueryClient
queryKey
queryFn
mutationFn
invalidateQueries
setQueryData
isLoading / isFetching / isPending
isError / error
onSuccess / onError
```

Outputs:

```text
atlas/index/tanstack-query-index.json
atlas/map/ui-state-map.json
atlas/graph/ui-to-api-graph.json
atlas/flows/ui-action-flows.json
```

## Material UI

Capture behaviour-significant component usage:

```text
TextField / Select / Checkbox / RadioGroup
Button / IconButton
Dialog / Modal / Drawer
Alert / Snackbar
Table / DataGrid-like views
disabled/loading/error props
form labels and accessibility hints
```

Outputs:

```text
atlas/index/material-ui-index.json
atlas/map/component-map.json
atlas/map/form-map.json
atlas/map/ui-state-map.json
```

## Leaflet / react-leaflet

Capture:

```text
MapContainer
TileLayer
Marker
Popup
Polyline / Polygon / Circle
GeoJSON
map event handlers
marker click/hover handlers
geospatial data sources
```

Semantic category: `geospatial_ui`.

## ReGraph

Capture:

```text
Graph / Chart-like ReGraph components
items/nodes/links props
selection handlers
layout/config props
node/link styling
expand/collapse interactions
```

Semantic category: `graph_visualization_ui`.

## Kiro AI enrichment packet

For each route/page packet, Kiro should identify:

```text
route path
page component
main user actions
forms and fields
queries and mutations
API clients called
loading/error/empty/success states
Leaflet/ReGraph visual semantics if present
Playwright test candidates
unknowns and needs_review items
```

## Do not infer

Do not infer backend enforcement, business rules, or OpenSearch behaviour from UI names alone. Link to backend/API/OpenSearch artifacts first, or mark the item as `needs_review: true`.
