# Runtime Context Mapping

CodeAtlas must capture runtime behaviour that wraps normal application code.

For backend APIs, not all behaviour is inside the endpoint function. Middleware, dependency injection, auth, logging, request IDs, exception handlers, background tasks, and runtime configuration can affect every request.

## Runtime artifacts

```text
atlas/runtime/middleware-map.yaml
atlas/runtime/dependency-map.yaml
atlas/runtime/exception-handler-map.yaml
atlas/runtime/logging-map.yaml
atlas/runtime/auth-map.yaml
atlas/runtime/config-map.yaml
atlas/runtime/feature-flag-map.yaml
```

## API flow envelope

API request flows should include a runtime envelope:

```yaml
runtime_envelope:
  before_endpoint:
    - middleware.request_logging
    - dependency.current_user
  after_endpoint:
    - middleware.response_logging
  exception_path:
    - handler.global_exception_handler
  needs_runtime_mapping: false
```

## Extraction targets

For FastAPI-style backends, Kiro should look for:

```text
app.add_middleware
@app.middleware
Depends(...)
exception_handler registrations
startup/shutdown handlers
background task creation
request logging wrappers
auth/session dependencies
settings/config objects
feature flags
```

## Confidence rule

Runtime findings are high confidence only when registration or usage is directly evidenced in code/config. Runtime config that depends on environment variables should usually be `confidence: medium` or `low` with `needs_review: true`.
