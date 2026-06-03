#!/usr/bin/env bash
set -euo pipefail

# Runs the main downstream planning/audit suite after Code Map + facts + domain artifacts exist.
# This does not mutate application repos. It creates CodeAtlas analysis/tooling artifacts.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python3 atlas/scripts/validate-artifacts.py --map

./atlas/scripts/run-framework-audit.sh
./atlas/scripts/run-code-health.sh
./atlas/scripts/run-visualizer-planner.sh
./atlas/scripts/run-test-planner.sh
./atlas/scripts/run-sample-data-planner.sh
./atlas/scripts/run-context-pack.sh

cat <<'EOF'
Downstream suite complete. Review:
- atlas/audit/
- atlas/code-health/
- atlas/visualizer/
- atlas/test-planning/
- atlas/sample-data/
- atlas/context-packs/
EOF
