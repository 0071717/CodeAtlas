#!/usr/bin/env python3
"""Compatibility entrypoint for the strict canonical CodeAtlas V2 runner."""
from __future__ import annotations

from codeatlas_v2_canonical_impl import *  # noqa: F401,F403
from codeatlas_v2_canonical_impl import main


if __name__ == "__main__":
    raise SystemExit(main())
