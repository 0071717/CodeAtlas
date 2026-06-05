#!/usr/bin/env python3
# CodeAtlas V2 deterministic foundation suite launcher.
# The executable source is stored as base64 chunks under codeatlas_v2_suite_payload/.
# This keeps the framework update deterministic while Kiro later refactors it into normal modules.
import base64
from pathlib import Path

payload_dir = Path(__file__).with_name('codeatlas_v2_suite_payload')
chunks = []
for path in sorted(payload_dir.glob('part*.b64')):
    chunks.append(path.read_text(encoding='utf-8'))
if not chunks:
    raise SystemExit('Missing payload chunks under atlas/tools/codeatlas_v2_suite_payload/')
source = base64.b64decode(''.join(chunks)).decode('utf-8')
exec(compile(source, __file__, 'exec'))
