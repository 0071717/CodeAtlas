#!/usr/bin/env python3
"""Compatibility entrypoint for the Atlas-native ngk CLI."""
from __future__ import annotations

from pathlib import Path
import sys

# Allow direct execution from a source checkout before editable install.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ngk_framework.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
