#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROMPTS_DIR="$ROOT_DIR/atlas/prompts"
LOG_DIR="$ROOT_DIR/atlas/logs/pr-impact-$(date +%Y-%m-%d_%H%M%S)"

mkdir -p "$LOG_DIR"
mkdir -p "$ROOT_DIR/atlas/maintenance"
cd "$ROOT_DIR"

AGENT="${KIRO_AGENT:-atlas-forge}"
DEFAULT_ARGS="${KIRO_DEFAULT_ARGS:---no-interactive --trust-all-tools}"
EXTRA_ARGS="${KIRO_EXTRA_ARGS:-}"

cat > "$LOG_DIR/PR_INPUTS.md" <<EOF
# PR Impact Inputs

Pass changed files / diff context to Kiro by editing this file or by setting context in your invocation.

Example:
- base branch: develop/foo
- head branch: feature/bar
- changed files:
  - backend/app/routers/knowledge_router.py
  - frontend/src/features/knowledge/SearchPanel.tsx
EOF

# shellcheck disable=SC2086
kiro-cli chat \
  --agent "$AGENT" \
  $DEFAULT_ARGS \
  $EXTRA_ARGS \
  "$(cat "$PROMPTS_DIR/23-pr-impact-analysis.md")" \
  2>&1 | tee "$LOG_DIR/23-pr-impact-analysis.log"

echo "PR impact analysis complete. Review atlas/maintenance/"
