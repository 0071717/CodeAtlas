#!/usr/bin/env python3
"""Compatibility entrypoint for the modular Atlas-native ngk CLI.

The implementation lives in focused modules so this file stays stable across
merges and remains safe for existing imports such as `ngk_framework.cli:main`.
"""
from __future__ import annotations

from .audit import AuditEngine, OutputParser, audit_answer, parse_citations
from .base import Workspace, file_hash_candidates
from .commands import build_parser, main
from .indexer import AtlasIndexer
from .store import AtlasStore

__all__ = [
    "AtlasIndexer",
    "AtlasStore",
    "AuditEngine",
    "OutputParser",
    "Workspace",
    "audit_answer",
    "build_parser",
    "file_hash_candidates",
    "main",
    "parse_citations",
]


if __name__ == "__main__":
    raise SystemExit(main())
