#!/usr/bin/env bash
set -euo pipefail

# Fully automated map-first mode:
# 1. architecture discovery / verification
# 2. repo health, repository census, domain map
# 3. semantic Code Map + technical facts
# 4. pilot domain
# 5. all remaining domains if pilot validates

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

./atlas/scripts/run-architecture-discovery.sh
./atlas/scripts/run-global.sh
./atlas/scripts/run-code-map.sh

python3 atlas/scripts/orchestrate_extraction.py --skip-global --auto-scale "$@"
