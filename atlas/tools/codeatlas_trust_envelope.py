#!/usr/bin/env python3
"""Compatibility entrypoint for trust/provenance envelope normalization."""
from __future__ import annotations

from codeatlas_trust_envelope_impl import *  # noqa: F401,F403
from codeatlas_trust_envelope_impl import main


if __name__ == "__main__":
    raise SystemExit(main())
