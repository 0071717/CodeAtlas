# Generated ngk Framework Bundle Manifest

This file records the generated framework packages produced during the Atlas/ngk design session. Codex should use this manifest together with `docs/CODEX_ATLAS_NGK_ENGINE_HANDOFF.md` to merge the prototype implementation into first-class repo code.

The generated ZIP bundles were:

```text
ngk-atlas-framework.zip
ngk-smart.zip
```

They contained two installable Python prototype packages:

```text
ngk-framework/
  pyproject.toml
  README.md
  docs/KIRO_UPGRADE_BRIEF.md
  ngk_framework/*.py
  examples/property-hub/**
  tests/test_framework.py

ngk-smart/
  pyproject.toml
  README.md
  ngk_smart/*.py
  examples/property-hub/**
  tests/test_parser.py
  tests/test_store.py
```

## Framework bundle file list

```text
ngk-framework/README.md
ngk-framework/docs/KIRO_UPGRADE_BRIEF.md
ngk-framework/ngk_framework/__init__.py
ngk-framework/ngk_framework/agent.py
ngk-framework/ngk_framework/audit.py
ngk-framework/ngk_framework/cli.py
ngk-framework/ngk_framework/config.py
ngk-framework/ngk_framework/context.py
ngk-framework/ngk_framework/indexer.py
ngk-framework/ngk_framework/io.py
ngk-framework/ngk_framework/models.py
ngk-framework/ngk_framework/output_parser.py
ngk-framework/ngk_framework/render.py
ngk-framework/ngk_framework/review.py
ngk-framework/ngk_framework/services.py
ngk-framework/ngk_framework/sessions.py
ngk-framework/ngk_framework/smart.py
ngk-framework/ngk_framework/workspace.py
ngk-framework/pyproject.toml
ngk-framework/tests/test_framework.py
ngk-framework/examples/property-hub/.atlas/facts/api_contracts.yaml
ngk-framework/examples/property-hub/.atlas/facts/data_contracts.yaml
ngk-framework/examples/property-hub/.atlas/facts/ui_contracts.yaml
ngk-framework/examples/property-hub/.atlas/manifest.json
ngk-framework/examples/property-hub/.atlas/status.json
ngk-framework/examples/property-hub/.atlas/traces/flow_traces.jsonl
ngk-framework/examples/property-hub/api/app/routers/property.py
ngk-framework/examples/property-hub/api/app/services/property_search.py
ngk-framework/examples/property-hub/ui/src/features/property/SearchPage.tsx
ngk-framework/examples/property-hub/ui/src/features/property/usePropertySearchQuery.ts
```

## Smart terminal bundle file list

```text
ngk-smart/README.md
ngk-smart/ngk_smart/__init__.py
ngk-smart/ngk_smart/cli.py
ngk-smart/ngk_smart/context_pack.py
ngk-smart/ngk_smart/io.py
ngk-smart/ngk_smart/kiro.py
ngk-smart/ngk_smart/models.py
ngk-smart/ngk_smart/output_parser.py
ngk-smart/ngk_smart/render.py
ngk-smart/ngk_smart/search.py
ngk-smart/ngk_smart/store.py
ngk-smart/ngk_smart/tui.py
ngk-smart/pyproject.toml
ngk-smart/tests/test_parser.py
ngk-smart/tests/test_store.py
ngk-smart/examples/property-hub/.atlas/citations/citation_index.jsonl
ngk-smart/examples/property-hub/.atlas/citations/source_cards.jsonl
ngk-smart/examples/property-hub/.atlas/facts/api_contracts.yaml
ngk-smart/examples/property-hub/.atlas/facts/data_contracts.yaml
ngk-smart/examples/property-hub/.atlas/facts/ui_contracts.yaml
ngk-smart/examples/property-hub/.atlas/indexes/source_spans.jsonl
ngk-smart/examples/property-hub/.atlas/manifest.json
ngk-smart/examples/property-hub/.atlas/retrieval/retrieval_index.jsonl
ngk-smart/examples/property-hub/.atlas/runtime/sessions/20260607T065205-how-does-property-search-work/context-pack.json
ngk-smart/examples/property-hub/.atlas/runtime/sessions/20260607T065205-how-does-property-search-work/context-pack.md
ngk-smart/examples/property-hub/.atlas/runtime/sessions/20260607T065205-how-does-property-search-work/question.md
ngk-smart/examples/property-hub/.atlas/runtime/sessions/20260607T065205-how-does-property-search-work/session.json
ngk-smart/examples/property-hub/.atlas/status.json
ngk-smart/examples/property-hub/.atlas/traces/flow_traces.jsonl
ngk-smart/examples/property-hub/api/app/routers/property.py
ngk-smart/examples/property-hub/api/app/services/property_search.py
ngk-smart/examples/property-hub/ui/src/features/property/SearchPage.tsx
ngk-smart/examples/property-hub/ui/src/features/property/usePropertySearchQuery.ts
```

## Preferred final merge shape

Codex should merge the overlapping prototypes into one package:

```text
tools/ngk-framework/
  pyproject.toml
  README.md
  ngk_framework/
    atlas/
    knowledge/
    impact/
    context/
    agents/
    sessions/
    smart/
  examples/
  tests/
```

The final package should expose one primary console command:

```bash
ngk
```

and optionally a compatibility alias:

```bash
ngk-smart
```

Prototype responsibility split:

```text
ngk_framework = core indexing, sessions, context packs, agent runner, audit
ngk_smart = smart terminal/TUI implementation
```

The two prototypes overlap. Prefer merging them instead of keeping duplicate CLIs indefinitely.

## Sandbox test status when generated

```text
ngk-atlas-framework: 5 passed
ngk-smart: parser/store tests passed in the generated sandbox
```

## Immediate Codex instruction

If the exact generated ZIPs are present in a local Codex workspace, materialize them, compare against this manifest, and then refactor into the package shape above. If the ZIPs are unavailable, use `tools/ngk_framework_mvp.py` as the bootstrap implementation and this manifest as the inventory of intended modules to recreate.
