# Repository Cleanup Audit

The canonical execution path is deterministic V2.

Keep:

- `atlas/tools/codeatlas_v2_suite.py`
- `atlas/tools/codeatlas_v2_canonical.py`
- `atlas/tools/codeatlas_preflight_doctor.py`
- `atlas/tools/ngk_trace_regraph_exporter.py`
- `atlas/tools/codeatlas_graph_report.py`
- `atlas/tools/codeatlas_query.py`

Treat old prompt-first scripts and broad future docs as legacy or future material, not the default path.

Generated Atlas outputs are ignored by default because they may contain target-project structure and behaviour.

Remaining gaps:

- legacy `.yaml` artifact names inside the V2 suite
- graph report not yet wired into the canonical `all` command
- candidate-only React extraction
- missing FastAPI route materialisation
- missing OpenSearch Query DSL reconstruction
