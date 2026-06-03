#!/usr/bin/env bash
set -euo pipefail

# Build the granular semantic Code Map and derive technical facts.
# This should run after architecture discovery, repo health, repository census, and domain map.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROMPTS_DIR="$ROOT_DIR/atlas/prompts"
LOG_DIR="$ROOT_DIR/atlas/logs/code-map-$(date +%Y-%m-%d_%H%M%S)"

mkdir -p "$LOG_DIR"
mkdir -p "$ROOT_DIR/atlas/map"
mkdir -p "$ROOT_DIR/atlas/facts"

cd "$ROOT_DIR"

AGENT="${KIRO_AGENT:-atlas-cartographer}"
DEFAULT_ARGS="${KIRO_DEFAULT_ARGS:---no-interactive --trust-all-tools}"
EXTRA_ARGS="${KIRO_EXTRA_ARGS:-}"

run_phase() {
  local prompt_file="$1"
  local log_file="$2"

  echo "=================================================="
  echo "Running CodeAtlas map phase: $prompt_file"
  echo "Agent: $AGENT"
  echo "Log: $LOG_DIR/$log_file"
  echo "=================================================="

  # shellcheck disable=SC2086
  kiro-cli chat \
    --agent "$AGENT" \
    $DEFAULT_ARGS \
    $EXTRA_ARGS \
    "$(cat "$PROMPTS_DIR/$prompt_file")" \
    2>&1 | tee "$LOG_DIR/$log_file"
}

run_phase "03a-code-map-extraction.md" "03a-code-map-extraction.log"
run_phase "03b-technical-facts.md" "03b-technical-facts.log"

python3 "$ROOT_DIR/atlas/scripts/validate-artifacts.py" --map

echo "Code Map extraction complete. Review:"
echo "  atlas/map/"
echo "  atlas/facts/technical-facts.yaml"
