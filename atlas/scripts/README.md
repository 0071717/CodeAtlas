# CodeAtlas Scripts

Use deterministic V2 first:

```bash
python3 atlas/tools/codeatlas_v2_canonical.py doctor
python3 atlas/tools/codeatlas_v2_canonical.py all
python3 atlas/tools/validate_artifacts.py atlas
python3 atlas/tools/codeatlas_graph_report.py
```

The `run-pre-transfer-check.sh` and `run-framework-v2-suite.sh` wrappers are convenience wrappers for the deterministic path.

Older prompt-first `run-*.sh` scripts are retained for reference and explicit opt-in use only. They are not the default path for a new target project.

## Cleanup rule

Do not delete legacy scripts blindly. If they are moved later, move them to `atlas/legacy/scripts/` and update docs in the same commit.
