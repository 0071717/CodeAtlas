#!/usr/bin/env bash
set -euo pipefail

# Builds the CodeAtlas foundation without running domain requirement extraction.
# Outputs:
# - atlas/architecture-discovery/
# - atlas/global/
# - atlas/map/
# - atlas/facts/

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

./atlas/scripts/run-architecture-discovery.sh
./atlas/scripts/run-global.sh
./atlas/scripts/run-code-map.sh

cat <<'EOF'
CodeAtlas foundation complete. Review:
- atlas/architecture-discovery/
- atlas/global/
- atlas/map/
- atlas/facts/technical-facts.yaml

Next options:
- ./atlas/scripts/run-pilot-auto.sh
- ./atlas/scripts/run-auto.sh
- ./atlas/scripts/run-downstream-suite.sh
EOF
