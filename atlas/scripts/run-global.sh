#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ATLAS_DIR="$ROOT_DIR/atlas"
PROMPTS_DIR="$ATLAS_DIR/prompts"
LOG_DIR="$ATLAS_DIR/logs/$(date +%Y-%m-%d_%H%M%S)-global"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

command -v kiro-cli >/dev/null 2>&1 || {
  echo "kiro-cli not found. Install/configure Kiro CLI first."
  exit 1
}

run_global_phase() {
  local phase_file="$1"
  local default_agent="$2"
  local log_name="$3"
  local agent="${KIRO_AGENT:-$default_agent}"
  local default_args="${KIRO_DEFAULT_ARGS:---no-interactive --trust-all-tools}"
  local extra_args="${KIRO_EXTRA_ARGS:-}"

  echo "=================================================="
  echo "Running global phase: $phase_file"
  echo "Agent: $agent"
  echo "Log: $LOG_DIR/$log_name"
  echo "=================================================="

  # shellcheck disable=SC2086
  kiro-cli chat \
    --agent "$agent" \
    $default_args \
    $extra_args \
    "$(cat "$PROMPTS_DIR/$phase_file")" \
    2>&1 | tee "$LOG_DIR/$log_name"
}

run_global_phase "00-repo-health-check.md" "atlas-cartographer" "00-repo-health-check.log"
run_global_phase "01-repository-census.md" "atlas-cartographer" "01-repository-census.log"
run_global_phase "02-domain-map.md" "atlas-cartographer" "02-domain-map.log"

python3 "$ATLAS_DIR/scripts/validate-artifacts.py" --global

echo "Global extraction phases complete."
