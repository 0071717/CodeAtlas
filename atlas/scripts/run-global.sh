#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EXTRACTION_DIR="$ROOT_DIR/atlas"
PROMPTS_DIR="$EXTRACTION_DIR/prompts"
LOG_DIR="$EXTRACTION_DIR/logs/$(date +%Y-%m-%d)"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

command -v kiro-cli >/dev/null 2>&1 || {
  echo "kiro-cli not found. Install/login to Kiro CLI first."
  exit 1
}

kiro-cli whoami >/dev/null || {
  echo "Kiro CLI is not authenticated. Run: kiro-cli login"
  exit 1
}

run_global_phase() {
  local phase_file="$1"
  local agent="$2"
  local log_name="$3"

  echo "=================================================="
  echo "Running global phase: $phase_file"
  echo "=================================================="

  kiro-cli chat \
    --agent "$agent" \
    --no-interactive \
    --trust-tools read,write,shell \
    "$(cat "$PROMPTS_DIR/$phase_file")" \
    2>&1 | tee "$LOG_DIR/$log_name"
}

run_global_phase "01-repository-census.md" "atlas-cartographer" "01-repository-census.log"
run_global_phase "02-domain-map.md" "atlas-cartographer" "02-domain-map.log"

python3 "$EXTRACTION_DIR/scripts/validate-artifacts.py" --global
echo "Global extraction phases complete."
