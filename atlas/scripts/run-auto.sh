#!/usr/bin/env bash
set -euo pipefail

# LEGACY / EXPLORATORY ONLY.
# Do not use this as the default first run for a new target project.
# Use the deterministic V2 path first:
#   python3 atlas/tools/codeatlas_v2_canonical.py doctor
#   python3 atlas/tools/codeatlas_v2_canonical.py all
#
# This script preserves the older automated map-first prompt workflow:
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
