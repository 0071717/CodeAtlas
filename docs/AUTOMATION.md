# Automation

CodeAtlas automation is map-first.

The main hands-off entrypoint is:

```bash
./atlas/scripts/run-auto.sh
```

It launches fresh Kiro CLI sessions for each phase and logs each phase under:

```bash
atlas/logs/<timestamp>/
```

## Environment setup

Use your Opus 4.6 agent if you have one:

```bash
export KIRO_AGENT="your-opus-agent-name"
export KIRO_DEFAULT_ARGS="--no-interactive --trust-all-tools"
```

Optional extra args:

```bash
export KIRO_EXTRA_ARGS="--model claude-opus-4.6"
```

Only use `KIRO_EXTRA_ARGS` if your Kiro CLI supports those flags. If model selection is handled by your custom agent, leave it empty.

## Map foundation only

```bash
./atlas/scripts/run-architecture-discovery.sh
./atlas/scripts/run-global.sh
./atlas/scripts/run-code-map.sh
```

This creates:

```text
atlas/architecture-discovery/
atlas/global/
atlas/map/
atlas/facts/
```

## Safer first run

```bash
./atlas/scripts/run-pilot-auto.sh
```

This runs architecture discovery, global discovery, Code Map extraction, technical facts, and one pilot domain.

## Full run

```bash
./atlas/scripts/run-auto.sh
```

This runs:

1. architecture discovery / verification
2. repo health / census / domain map
3. semantic Code Map extraction
4. technical fact extraction
5. pilot domain extraction
6. remaining domain extraction

## One domain only

Run after global/map outputs exist:

```bash
python3 atlas/scripts/orchestrate_extraction.py --skip-global --only-domain customer_management
```

or:

```bash
./atlas/scripts/run-domain.sh customer_management
```

## Use a specific pilot

```bash
python3 atlas/scripts/orchestrate_extraction.py --pilot-domain customer_management --auto-scale
```

## Validate outputs

```bash
python3 atlas/scripts/validate-artifacts.py --global
python3 atlas/scripts/validate-artifacts.py --map
python3 atlas/scripts/validate-artifacts.py --all
```

## Downstream tooling automation

After map/facts/domain artifacts exist:

```bash
./atlas/scripts/run-framework-audit.sh
./atlas/scripts/run-code-health.sh
./atlas/scripts/run-visualizer-planner.sh
./atlas/scripts/run-test-planner.sh
./atlas/scripts/run-sample-data-planner.sh
./atlas/scripts/run-context-pack.sh
```

Or run the main downstream suite:

```bash
./atlas/scripts/run-downstream-suite.sh
```

## Maintenance automation

```bash
./atlas/scripts/run-pr-impact.sh
./atlas/scripts/run-release-governance.sh
```

These are scaffolds for ongoing development, PR impact analysis, and release branch governance.

## Important caveat

If your Kiro setup only allows model switching through interactive `/model`, scripts cannot reliably automate that slash command. Set the desired model once in Kiro or configure it in your custom agent.
