# Automation

The main hands-off entrypoint is:

```bash
./atlas/scripts/run-auto.sh
```

This launches a new Kiro CLI session for every phase.

Each phase is independent and logged under:

```bash
atlas/logs/<timestamp>/
```

## Safer first run

```bash
./atlas/scripts/run-pilot-auto.sh
```

This stops after one pilot domain.

## Full run

```bash
./atlas/scripts/run-auto.sh
```

## One domain only

```bash
python3 atlas/scripts/orchestrate_extraction.py --only-domain customer_management
```

## Use a specific pilot

```bash
python3 atlas/scripts/orchestrate_extraction.py --pilot-domain customer_management --auto-scale
```

## Extra Kiro args

```bash
export KIRO_EXTRA_ARGS="--model claude-opus-4.6"
./atlas/scripts/run-auto.sh
```

## Important caveat

If your Kiro setup only allows model switching through interactive `/model`, the script cannot reliably automate that slash command. Set the desired model once in Kiro or configure it in the agent/model settings supported by your Kiro installation.
