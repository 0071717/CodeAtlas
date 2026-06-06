# Repository Cleanup Policy

CodeAtlas should stay compact enough for Kiro, developer CLIs, and reviewers to
load without fighting stale entrypoints. Cleanup must not erase project memory.

## Canonicalization rules

1. Prefer one canonical document per topic.
2. When retiring standalone docs, move their still-relevant content into the
   canonical replacement first.
3. Keep historical detail in `docs/CHANGELOG.md` and future-work detail in
   `docs/ROADMAP_AND_IMPLEMENTATION_PLAN.md` instead of scattering dated files.
4. Update every prompt, README, and handoff guide that referenced a retired file.
5. Do not delete schemas, prompts, scripts, or tool outputs unless a replacement
   path is documented and references are updated.

## Current canonical replacements

| Retired pattern | Canonical destination |
|---|---|
| `docs/KIRO_CHANGELOG*.md` | `docs/CHANGELOG.md` |
| `docs/NEXT_STEPS_FOR_KIRO.md` | `docs/ROADMAP_AND_IMPLEMENTATION_PLAN.md` |
| `docs/TOOLING_ROADMAP.md` | `docs/ROADMAP_AND_IMPLEMENTATION_PLAN.md` |
| `docs/IMPLEMENTATION_TICKETS_PRE_TRANSFER.md` | `docs/ROADMAP_AND_IMPLEMENTATION_PLAN.md` |

## Safety checklist before deleting a file

```bash
rg -n "<file-name>" README.md docs atlas/prompts atlas/scripts atlas/tools
python3 atlas/tools/codeatlas_v2_canonical.py doctor
python3 atlas/tools/codeatlas_v2_canonical.py all
```

If references remain, update them or keep the file.
