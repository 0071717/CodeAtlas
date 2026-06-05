# Multi-Repo Mapping Strategy

CodeAtlas V2 should support more than one application repo.

A mature system may store behaviour in several places:

```text
frontend repo
backend repo
shared contracts repo
search/config repo
sample-data repo
test-support repo
documentation repo
```

## Source coverage rule

Every configured repo should be included in:

```text
atlas/source/snapshot.yaml
atlas/source/file-hashes.yaml
atlas/index/file-index.yaml
```

Even if a repo has no deep extractor yet, it should still be hash-tracked so drift can be detected.

## Suggested repo roles

```text
react_frontend
fastapi_backend
shared_contracts
opensearch_config
sample_data_generation
test_support
documentation
```

## Role-specific extraction

Frontend repos should map routes, pages, components, hooks, forms, actions, API clients, UI states, and UI tests.

Backend repos should map routers, endpoints, schemas, services, data access, middleware, dependencies, errors, permissions, and backend tests.

Search/config repos should map index names, aliases, mappings, field types, analyzers, settings, templates, and migration scripts.

Sample-data repos should map factories, seed scripts, fixture scenarios, test users, roles, and scenario coverage.

Documentation repos should be indexed and used only as secondary context. Source code remains authoritative for current behaviour.

## Cross-repo graph examples

```text
frontend API client MAPS_TO backend endpoint
backend data access READS search index
backend data access WRITES search index
backend test USES fixture
sample-data scenario SUPPORTS UI flow
shared contract DEFINES frontend/backend type
```

## Missing extractor rule

If a repo role is configured but the specific extractor does not exist yet, Kiro should still snapshot and file-index the repo, then emit a `needs_extractor` finding instead of ignoring it.
