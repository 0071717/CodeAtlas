#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROMPTS_DIR="$ROOT_DIR/atlas/prompts"
LOG_DIR="$ROOT_DIR/atlas/logs/test-planner-$(date +%Y-%m-%d_%H%M%S)"

mkdir -p "$LOG_DIR"
mkdir -p "$ROOT_DIR/atlas/test-planning"
cd "$ROOT_DIR"

AGENT="${KIRO_AGENT:-atlas-forge}"
DEFAULT_ARGS="${KIRO_DEFAULT_ARGS:---no-interactive --trust-all-tools}"
EXTRA_ARGS="${KIRO_EXTRA_ARGS:-}"

# shellcheck disable=SC2086
kiro-cli chat \
  --agent "$AGENT" \
  $DEFAULT_ARGS \
  $EXTRA_ARGS \
  "$(cat "$PROMPTS_DIR/22-playwright-test-planner.md")" \
  2>&1 | tee "$LOG_DIR/22-playwright-test-planner.log"

echo "Playwright/test planning complete. Review atlas/test-planning/"
