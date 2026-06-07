"""Compatibility smoke tests for legacy ngk_framework.cli imports."""
from __future__ import annotations

from ngk_framework.cli import AtlasIndexer, AtlasStore, Workspace, file_hash_candidates, main, parse_citations


def test_cli_compatibility_exports() -> None:
    assert AtlasIndexer is not None
    assert AtlasStore is not None
    assert Workspace is not None
    assert file_hash_candidates is not None
    assert main is not None
    parsed = parse_citations('[fact.api.property_search.endpoint]')
    assert parsed["fact_ids"] == ["fact.api.property_search.endpoint"]
