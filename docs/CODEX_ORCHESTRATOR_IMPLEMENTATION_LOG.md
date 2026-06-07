# Codex Orchestrator Implementation Log

This branch implements the no-MCP ngk orchestrator framework.

## Follow-up assessment

The first Codex pass added useful scaffolding, but it was too shallow in several important places. The branch now has a corrective commit that hardens Kiro custom-agent generation so generated agents remain no-MCP, use structured hooks, restrict shell to `ngk tool ...` commands, and keep `includeMcpJson` disabled.

Remaining improvements to apply locally if not already present:

- Package `ngk_orchestrator.kiro_hooks` in `pyproject.toml`.
- Strengthen hook guard behavior and test it against denied secret paths, nested orchestration, and read-only write attempts.
- Replace one-line prompt/rule files with detailed agent scope, citation, support taxonomy, and prompt-injection boundary rules.
- Improve synthesis schema to emit `status`, `overall_verdict`, accepted/rejected findings, conflicts, known unknowns, recommended tests, and final summary.
- Make `ngk orchestrations show` default to `latest`.
- Add `ngk delegate critic` and richer plan/debug/implement dry-run orchestration.
- Ensure cross-stack review is triggered for UI/API boundary changes.

## Validation to run

```bash
python3 -m pip install -e '.[dev]'
pytest tests/ngk_framework
ngk atlas index --atlas examples/ngk-property-hub/.atlas
ngk agents validate
ngk agents generate-kiro
ngk hooks install
ngk hooks validate
ngk orchestrate review --changed --no-agent --atlas examples/ngk-property-hub/.atlas
ngk orchestrate review --changed --read-only --agent mock --atlas examples/ngk-property-hub/.atlas
ngk synthesize latest
ngk smart --orchestration latest
```
