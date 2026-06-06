#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile \
  atlas/tools/codeatlas_v2_suite.py \
  atlas/tools/codeatlas_v2_canonical.py \
  atlas/tools/codeatlas_preflight_doctor.py \
  atlas/tools/codeatlas_artifact_validator.py \
  atlas/tools/codeatlas_graph_report.py \
  atlas/tools/codeatlas_graph_html.py \
  atlas/tools/codeatlas_query.py \
  atlas/tools/ngk_trace_regraph_exporter.py

python3 atlas/tools/codeatlas_v2_canonical.py doctor
python3 atlas/tools/codeatlas_artifact_validator.py || true
