# CodeAtlas Active Scripts

Active scripts should be small wrappers around deterministic V2 tools.

## Canonical wrappers

```bash
bash atlas/scripts/run-pre-transfer-check.sh
bash atlas/scripts/run-framework-v2-suite.sh
```

Equivalent direct commands:

```bash
python3 atlas/tools/codeatlas_v2_canonical.py doctor
python3 atlas/tools/codeatlas_v2_canonical.py all
```

## Legacy wrappers

Older prompt-first / map-first orchestration scripts were moved to:

```text
atlas/legacy/scripts/
```

Do not reintroduce old prompt-first scripts here unless they are clearly marked as legacy and cannot be mistaken for the canonical path.

## Cleanup rule

Do not delete legacy scripts blindly. If they are moved later, move them to `atlas/legacy/scripts/` and update docs in the same commit.
