#!/usr/bin/env bash
set -euo pipefail

cat >&2 <<'EOF'
run-auto.sh is a legacy prompt-first CodeAtlas entrypoint.

The deterministic V2 path is canonical. Use:

  python3 atlas/tools/codeatlas_v2_canonical.py doctor
  python3 atlas/tools/codeatlas_v2_canonical.py all

The historical script content is preserved at:

  atlas/legacy/scripts/run-auto.sh

Run that legacy script only if you explicitly want the old prompt-first workflow.
EOF

exit 2
