#!/usr/bin/env bash
set -euo pipefail

# Safer first run:
# - runs global phases
# - auto-selects one pilot domain
# - stops after pilot

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

python3 atlas/scripts/orchestrate_extraction.py "$@"
