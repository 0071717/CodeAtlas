#!/usr/bin/env bash
set -euo pipefail

DOMAIN_ID="${1:-}"

if [[ -z "$DOMAIN_ID" ]]; then
  echo "Usage: $0 <domain_id>"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
EXTRACTION_DIR="$ROOT_DIR/atlas"
PROMPTS_DIR="$EXTRACTION_DIR/prompts"
LOG_DIR="$EXTRACTION_DIR/logs/$(date +%Y-%m-%d)"
DOMAIN_DIR="$EXTRACTION_DIR/domains/$DOMAIN_ID"

mkdir -p "$LOG_DIR"
mkdir -p "$DOMAIN_DIR"

run_phase() {
  local phase_file="$1"
  local agent="$2"
  local log_name="$3"

  echo "=================================================="
  echo "Running $phase_file for domain $DOMAIN_ID"
  echo "Agent: $agent"
  echo "=================================================="

  local prompt
  prompt="$(cat "$PROMPTS_DIR/$phase_file")"
  prompt="${prompt//<DOMAIN_ID>/$DOMAIN_ID}"

  (
    cd "$ROOT_DIR"
    kiro-cli chat \
      --agent "$agent" \
      --no-interactive \
      --trust-tools read,write,shell \
      "$prompt"
  ) 2>&1 | tee "$LOG_DIR/$log_name"

  echo "Completed $phase_file"
}

run_phase "03-domain-scope.md" "domain-scout" "$DOMAIN_ID-03-domain-scope.log"
run_phase "04-backend-technical-rules.md" "domain-scout" "$DOMAIN_ID-04-backend-technical-rules.log"
run_phase "05-frontend-technical-rules.md" "domain-scout" "$DOMAIN_ID-05-frontend-technical-rules.log"
run_phase "06-contract-mapping.md" "domain-scout" "$DOMAIN_ID-06-contract-mapping.log"
run_phase "07-business-rules.md" "domain-scout" "$DOMAIN_ID-07-business-rules.log"
run_phase "08-user-stories.md" "domain-scout" "$DOMAIN_ID-08-user-stories.log"
run_phase "09-epics-hlrs.md" "domain-scout" "$DOMAIN_ID-09-epics-hlrs.log"
run_phase "10-contradictions-dead-code.md" "rift-hunter" "$DOMAIN_ID-10-contradictions-dead-code.log"
run_phase "11-update-kiro-steering.md" "memory-smith" "$DOMAIN_ID-11-update-kiro-steering.log"
run_phase "12-review-pack.md" "domain-scout" "$DOMAIN_ID-12-review-pack.log"

python3 "$EXTRACTION_DIR/scripts/validate-artifacts.py" "$DOMAIN_ID"

echo "Domain extraction completed: $DOMAIN_ID"
