# React UI Stack Mapping Guide

This guide specializes CodeAtlas frontend extraction for projects using:

```text
React
TypeScript
React Router DOM
TanStack Query
Material UI
```

## Frontend model

For this stack, UI behaviour should be mapped as:

```text
React Router route
→ page/layout component
→ Material UI layout/form/action components
→ local state/form state
→ TanStack Query query or mutation hook
→ API client
→ backend endpoint
→ loading/error/success/empty UI states
```

## React Router DOM extraction targets

Look for:

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
loader/action only if used
```

Capture:

```yaml
routes:
  - id: route.claims.new
    path: /claims/new
    file: src/routes/AppRoutes.tsx
    page_component: component.claims.NewClaimPage
    params: []
    nested_under: route.claims.root
    auth_required: unknown
    confidence: medium
    needs_review: true
```

## TanStack Query extraction targets

Look for:

```text
useQuery
useMutation
useInfiniteQuery
queryClient.invalidateQueries
queryClient.setQueryData
queryClient.refetchQueries
mutation.mutate
mutation.mutateAsync
isLoading / isPending / isFetching
isError
isSuccess
error
data
```

Capture query hooks:

```yaml
query_hooks:
  - id: hook.claims.useClaimsQuery
    kind: tanstack_query
    query_key: claims
    calls_api: api.claims.listClaims
    states:
      loading: isLoading or isFetching
      error: isError or error
      success: data available
    cache_effects: []
    confidence: medium
    needs_review: true
```

Capture mutation hooks:

```yaml
mutation_hooks:
  - id: hook.claims.useCreateClaimMutation
    kind: tanstack_mutation
    calls_api: api.claims.createClaim
    success_effects:
      - invalidate query claims
      - show success toast if present
      - navigate if present
    error_effects:
      - show error alert/snackbar if present
    confidence: medium
    needs_review: true
```

## Material UI extraction targets

Look for meaningful UI components, not every MUI element.

High-value components:

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

Capture:

```text
form fields
action buttons
modal/dialog flows
loading indicators
error alerts/snackbars
empty states
data tables/grids
permission-disabled or hidden actions
```

Do not map every `Box`, `Stack`, `Grid`, or typography element unless it affects behaviour.

## UI state model

For every route/page or form flow, capture:

```text
initial
loading
empty
populated
validation_error
server_error
permission_denied
success
disabled
navigation_redirect
```

Example:

```yaml
ui_states:
  - id: state.claims.create.loading
    route: route.claims.new
    triggered_by: hook.claims.useCreateClaimMutation.isPending
    visible:
      - action.claims.submit.loading
    disabled:
      - action.claims.submit
    confidence: medium
    needs_review: true
```

## UI flow shape

```yaml
ui_flows:
  - id: flow.ui.claims.create_claim
    route: route.claims.new
    page: component.claims.NewClaimPage
    steps:
      - order: 1
        type: navigate
        target: route.claims.new
      - order: 2
        type: render
        target: component.claims.ClaimForm
      - order: 3
        type: user_input
        target: form.claims.create
      - order: 4
        type: submit
        target: action.claims.submit
      - order: 5
        type: tanstack_mutation
        target: hook.claims.useCreateClaimMutation
      - order: 6
        type: api_call
        target: api.claims.createClaim
      - order: 7
        type: success_or_error_state
        target: state.claims.create.result
    confidence: medium
    needs_review: true
```

## AI-assisted frontend extraction strategy

A good AI worker should process one route or page cluster at a time:

```text
1. Read route index.
2. Select one route/page.
3. Read the page component and direct child form/action/hook files.
4. Identify React Router params/navigation.
5. Identify TanStack Query query/mutation hooks.
6. Identify Material UI fields/actions/states.
7. Link API clients to backend endpoint candidates.
8. Write component/form/state/flow YAML.
9. Mark uncertain findings needs_review.
```

## Test generation implications

For Playwright tests, use this stack mapping to generate:

```text
route render tests
happy path mutation tests
required field validation tests
server error display tests
loading/disabled submit tests
empty state tests
table/grid data display tests
permission hidden/disabled action tests
navigation success tests
cache invalidation side-effect tests where observable
```
