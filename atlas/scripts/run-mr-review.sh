#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROMPTS_DIR="$ROOT_DIR/atlas/prompts"
MR_IID="${CODEATLAS_MR_IID:-${1:-}}"

if [[ -z "$MR_IID" ]]; then
  echo "Usage: CODEATLAS_MR_IID=<iid> $0"
  echo "   or: $0 <iid>"
  exit 1
fi

export CODEATLAS_MR_IID="$MR_IID"
export CODEATLAS_REVIEW_MODE="${CODEATLAS_REVIEW_MODE:-draft}"
export CODEATLAS_POST_REVIEW_COMMENTS="${CODEATLAS_POST_REVIEW_COMMENTS:-false}"
export CODEATLAS_REVIEW_APPROVED="${CODEATLAS_REVIEW_APPROVED:-false}"

LOG_DIR="$ROOT_DIR/atlas/logs/mr-review-${MR_IID}-$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$LOG_DIR"
mkdir -p "$ROOT_DIR/atlas/reviews/mr-${MR_IID}"
cd "$ROOT_DIR"

AGENT="${KIRO_AGENT:-atlas-forge}"
DEFAULT_ARGS="${KIRO_DEFAULT_ARGS:---no-interactive --trust-all-tools}"
EXTRA_ARGS="${KIRO_EXTRA_ARGS:-}"

cat > "$ROOT_DIR/atlas/reviews/mr-${MR_IID}/review-env.txt" <<EOF
CODEATLAS_MR_IID=$CODEATLAS_MR_IID
CODEATLAS_REVIEW_MODE=$CODEATLAS_REVIEW_MODE
CODEATLAS_POST_REVIEW_COMMENTS=$CODEATLAS_POST_REVIEW_COMMENTS
CODEATLAS_REVIEW_APPROVED=$CODEATLAS_REVIEW_APPROVED
EOF

# shellcheck disable=SC2086
kiro-cli chat \
  --agent "$AGENT" \
  $DEFAULT_ARGS \
  $EXTRA_ARGS \
  "$(cat "$PROMPTS_DIR/33-merge-request-review.md")" \
  2>&1 | tee "$LOG_DIR/33-merge-request-review.log"

if [[ "$CODEATLAS_REVIEW_MODE" != "approved-post" || "$CODEATLAS_POST_REVIEW_COMMENTS" != "true" || "$CODEATLAS_REVIEW_APPROVED" != "true" ]]; then
  echo "MR review completed in draft/prepare mode. No review comments were posted."
  echo "Review atlas/reviews/mr-${MR_IID}/ before approving any glab post commands."
else
  echo "MR review completed with posting approved by environment flags. Check atlas/reviews/mr-${MR_IID}/ for executed command notes."
fi
