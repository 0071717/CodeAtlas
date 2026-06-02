#!/usr/bin/env bash
set -euo pipefail

# Fully automated mode:
# - runs global phases
# - auto-selects a pilot domain
# - runs pilot
# - if pilot validates, runs all remaining domains

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python3 atlas/scripts/orchestrate_extraction.py --auto-scale "$@"
