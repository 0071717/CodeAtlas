#!/usr/bin/env bash
set -euo pipefail

python3 atlas/tools/codeatlas_v2_canonical.py all
python3 atlas/tools/codeatlas_artifact_validator.py
python3 atlas/tools/codeatlas_graph_report.py || true
python3 atlas/tools/codeatlas_graph_html.py || true
