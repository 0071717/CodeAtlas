# CodeAtlas Tooling Roadmap

CodeAtlas YAML is intended to be a reusable foundation, not a single-purpose extraction output.

The core foundation is:

```text
atlas/map/*.yaml
atlas/facts/technical-facts.yaml
atlas/domains/*/*.yaml
```

Downstream tools should read these artifacts rather than repeatedly scanning raw source code.

## Tool categories

| Tool | Inputs | Outputs | Purpose |
|---|---|---|---|
| Code visualizer | `atlas/map` | graph/UI data | Explore routes, endpoints, services, UI flows, rules |
| PR impact analyzer | changed files + `atlas/map` | PR impact report | Identify affected domains, rules, tests, UI screens |
| Code health analyzer | `atlas/map` + facts | health scores, violations | Improve architecture and consistency |
| Contract checker | `api-map`, `schema-map`, `validation-map` | mismatches | Detect frontend/backend drift |
| Playwright generator | `ui-flow-map`, `api-map`, stories | test specs | Generate user-flow E2E tests |
| API test generator | `backend-map`, `schema-map`, facts | API tests | Generate endpoint tests from contracts/rules |
| Test gap analyzer | facts/rules + test evidence | coverage gaps | Find important behaviour without tests |
| Sample data generator | schemas + state map + stories | seed fixtures | Create realistic test/dev data |
| Debug navigator | map + facts + errors | debugging paths | Show likely files/functions for a bug |
| Refactor planner | call graph + health | refactor tickets | Safely improve messy areas |
| Release impact reporter | baseline + branch delta | release report | Explain behaviour changes by release |
| Kiro context packer | selected domain map | `.md` context pack | Give dev agents compact project context |

## Build order

Recommended order:

1. Code Map visualizer data exporter
2. PR impact analyzer
3. Contract checker
4. Code health analyzer
5. Test gap analyzer
6. Playwright test generator
7. Sample data generator
8. Release governance tools
9. Interactive web UI

## Tool design principles

- Read YAML artifacts first.
- Do not rescan raw code unless the map is missing information.
- Prefer deterministic parsing and graph traversal before LLM reasoning.
- Keep outputs reviewable and diffable.
- Preserve stable IDs.
- Avoid overwriting approved rules without marking them superseded.
- Separate advisory findings from blocking findings.

## Custom Kiro agent

Use `.kiro/agents/atlas-forge.json` for tool building.

Typical command:

```bash
export KIRO_AGENT="atlas-forge"
export KIRO_DEFAULT_ARGS="--no-interactive --trust-all-tools"
kiro-cli chat --agent atlas-forge --no-interactive --trust-all-tools "$(cat atlas/prompts/20-build-tool-from-map.md)"
```

You can also override with your Opus agent:

```bash
export KIRO_AGENT="your-opus-agent-name"
./atlas/scripts/run-tool-planner.sh
```
