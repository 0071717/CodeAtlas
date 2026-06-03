#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROMPTS_DIR="$ROOT_DIR/atlas/prompts"
LOG_DIR="$ROOT_DIR/atlas/logs/release-governance-$(date +%Y-%m-%d_%H%M%S)"

mkdir -p "$LOG_DIR"
mkdir -p "$ROOT_DIR/atlas/releases"
cd "$ROOT_DIR"

AGENT="${KIRO_AGENT:-atlas-forge}"
DEFAULT_ARGS="${KIRO_DEFAULT_ARGS:---no-interactive --trust-all-tools}"
EXTRA_ARGS="${KIRO_EXTRA_ARGS:-}"

# shellcheck disable=SC2086
kiro-cli chat \
  --agent "$AGENT" \
  $DEFAULT_ARGS \
  $EXTRA_ARGS \
  "$(cat "$PROMPTS_DIR/24-release-governance.md")" \
  2>&1 | tee "$LOG_DIR/24-release-governance.log"

echo "Release governance artifacts complete. Review atlas/releases/"
