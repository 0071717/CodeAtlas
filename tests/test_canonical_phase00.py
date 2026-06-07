from __future__ import annotations

# Compatibility test module kept because the first Phase 00 Codex attempt added
# this filename. The authoritative Phase 00 tests now live in:
# - tests/test_canonical_strict_mode.py
# - tests/test_run_manifest.py
# - tests/test_strict_pipeline_order.py

from tests.test_run_manifest import test_run_manifest_uses_required_path_schema_and_fields
from tests.test_strict_pipeline_order import test_all_strict_stops_before_sqlite_when_validation_fails
