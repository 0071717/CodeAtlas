#!/usr/bin/env python3
# CodeAtlas V2 deterministic foundation suite launcher.
# The executable payload is split into base64 chunks so the framework can be updated safely through GitHub contents API.
# Kiro should treat this as a generated launcher and improve it into normal source modules over time.
import base64
from pathlib import Path

PAYLOAD_DIR = Path(__file__).with_name('codeatlas_v2_suite_payload')
parts = []
for path in sorted(PAYLOAD_DIR.glob('part*.b64')):
    parts.append(path.read_text(encoding='utf-8'))
if not parts:
    raise SystemExit('Missing CodeAtlas V2 payload chunks under atlas/tools/codeatlas_v2_suite_payload/')
source = base64.b64decode(''.join(parts)).decode('utf-8')
exec(compile(source, __file__, 'exec'))
