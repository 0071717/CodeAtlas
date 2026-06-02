#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EXTRACTION_DIR="$ROOT_DIR/atlas"

cd "$ROOT_DIR"

echo "Running global phases..."
"$EXTRACTION_DIR/scripts/run-global.sh"

DOMAINS="$(python3 "$EXTRACTION_DIR/scripts/list-domains.py")"

echo "Domains found:"
echo "$DOMAINS"

for domain in $DOMAINS; do
  echo "Running extraction for domain: $domain"
  "$EXTRACTION_DIR/scripts/run-domain.sh" "$domain"
done

python3 "$EXTRACTION_DIR/scripts/validate-artifacts.py" --all

echo "Full CodeAtlas extraction completed."
