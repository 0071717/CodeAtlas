# Workflow

## Recommended run order

```bash
kiro-cli whoami
./atlas/scripts/run-global.sh
python3 atlas/scripts/list-domains.py
./atlas/scripts/run-domain.sh <pilot_domain_id>
```

Review the pilot output before running:

```bash
./atlas/scripts/run-extraction.sh
```

## Quality gate

Before scaling to all domains, inspect:

- technical rules
- code references
- contradictions
- review notes

The output is good only if requirements are specific and code-traceable.
