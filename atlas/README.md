# CodeAtlas Pipeline

This folder contains the machine-readable CodeAtlas pipeline.

`atlas/` is the detailed source of truth.

`.kiro/steering/` is compact working memory for Kiro and future AI-assisted development tasks.

## Foundation model

CodeAtlas is now **architecture-first** and **map-first**.

The preferred flow is:

```text
Raw code
→ Architecture discovery
→ Repo inventory
→ Granular Code Map YAML
→ Technical facts
→ Technical rules
→ Business rules
→ User stories
→ Epics
→ High-Level Requirements
```

The granular YAML map under `atlas/map/` is the reusable foundation for many tools, not just requirements extraction.

## Important directories

```text
atlas/
  architecture-discovery/   # Kiro-derived architecture drafts, verified architecture, traversal guide
  config/                   # project config, extraction policy, schemas
  prompts/                  # bounded Kiro prompts for each phase
  scripts/                  # automation entrypoints
  global/                   # repo health, inventories, global domain map
  map/                      # semantic codebase map
  facts/                    # technical facts derived from the map
  domains/                  # domain-level rules, stories, contradictions, review packs
  releases/                 # release baselines and release impact reports
  logs/                     # Kiro run logs
```

## Core commands

Architecture discovery:

```bash
./atlas/scripts/run-architecture-discovery.sh
```

Build semantic Code Map and technical facts:

```bash
./atlas/scripts/run-code-map.sh
```

Pilot extraction:

```bash
./atlas/scripts/run-pilot-auto.sh
```

Full extraction:

```bash
./atlas/scripts/run-auto.sh
```

## Map-first rule

Do not ask Kiro to derive business rules directly from raw source code where avoidable.

Prefer:

```text
code map
→ technical facts
→ technical rules
→ business rules
```

This gives better traceability, more stable diffs, and reusable artifacts for PR impact analysis, code health checks, release governance, refactor planning, and interactive UIs.
