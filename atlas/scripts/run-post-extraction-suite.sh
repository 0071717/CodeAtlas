#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "Step 1/3: Normalizing Atlas outputs into atlas/knowledge/"
"$ROOT_DIR/atlas/scripts/run-knowledge-normalizer.sh"

echo "Step 2/3: Running Code ↔ Atlas reverse verification"
"$ROOT_DIR/atlas/scripts/run-reverse-verification.sh"

echo "Step 3/3: Refreshing Kiro context packs and steering files"
"$ROOT_DIR/atlas/scripts/run-context-refresh.sh"

echo "Post-extraction suite complete. Review:"
echo "- atlas/knowledge/"
echo "- atlas/knowledge/audit/"
echo "- atlas/context-packs/"
echo "- .kiro/steering/"
