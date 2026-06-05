#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROMPTS_DIR="$ROOT_DIR/atlas/prompts"
LOG_DIR="$ROOT_DIR/atlas/logs/knowledge-normalizer-$(date +%Y-%m-%d_%H%M%S)"

mkdir -p "$LOG_DIR"
mkdir -p "$ROOT_DIR/atlas/knowledge/nodes"
mkdir -p "$ROOT_DIR/atlas/knowledge/indexes"
mkdir -p "$ROOT_DIR/atlas/knowledge/graph"
mkdir -p "$ROOT_DIR/atlas/knowledge/cards"
mkdir -p "$ROOT_DIR/atlas/knowledge/audit"
cd "$ROOT_DIR"

AGENT="${KIRO_AGENT:-atlas-forge}"
DEFAULT_ARGS="${KIRO_DEFAULT_ARGS:---no-interactive --trust-all-tools}"
EXTRA_ARGS="${KIRO_EXTRA_ARGS:-}"

# shellcheck disable=SC2086
kiro-cli chat \
  --agent "$AGENT" \
  $DEFAULT_ARGS \
  $EXTRA_ARGS \
  "$(cat "$PROMPTS_DIR/30-knowledge-normalizer.md")" \
  2>&1 | tee "$LOG_DIR/30-knowledge-normalizer.log"

echo "Knowledge normalization complete. Review atlas/knowledge/"
