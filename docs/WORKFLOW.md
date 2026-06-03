# Workflow

## Philosophy

CodeAtlas is architecture-first.

Do not start by extracting requirements.

First teach Kiro how the system is structured.

The recommended progression is:

```text
Architecture Discovery
→ Architecture Verification
→ Repo Health Check
→ Repository Census
→ Domain Map
→ Pilot Domain Extraction
→ Full Extraction
→ Ongoing Maintenance
```

## Recommended first run

```bash
export KIRO_AGENT="your-opus-agent-name"
export KIRO_DEFAULT_ARGS="--no-interactive --trust-all-tools"

./atlas/scripts/run-architecture-discovery.sh
```

Review:

```text
atlas/architecture-discovery/human-review-checklist.md
atlas/architecture-discovery/extraction-traversal-guide.md
```

Then:

```bash
./atlas/scripts/run-pilot-auto.sh
```

Review the pilot domain output before scaling.

## Full extraction

```bash
./atlas/scripts/run-auto.sh
```

This performs:

1. architecture discovery
2. architecture verification
3. repo health check
4. repository census
5. domain map
6. pilot domain extraction
7. validation
8. remaining domains

## Quality gate

Before scaling to all domains, inspect:

- architecture verification documents
- extraction traversal guide
- technical rules
- code references
- contract mappings
- contradictions
- review notes

The output is only considered good if:

- requirements are specific
- requirements are traceable to code
- frontend/backend behaviour is distinguished correctly
- contradictions are surfaced
- architecture assumptions are evidenced

## Maintenance lifecycle

After the initial extraction, CodeAtlas becomes a living baseline.

Recommended ongoing flow:

```text
Pull Request
→ Impact Analysis
→ Targeted Domain Extraction
→ Rule Delta
→ Contradiction Scan
→ Review
→ Baseline Update
```

See:

```text
docs/MAINTENANCE_STRATEGY.md
```
