from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ngk_framework.cli import AtlasIndexer, AtlasStore, Workspace, parse_citations

ROOT = Path(__file__).resolve().parents[2]
ATLAS = ROOT / "examples" / "ngk-property-hub" / ".atlas"


def test_indexer_loads_property_hub(tmp_path: Path) -> None:
    ws = Workspace(ROOT, str(ATLAS), str(tmp_path / ".ngk"))
    counts = AtlasIndexer(ws).index()
    assert counts == {"facts": 3, "evidence": 4, "spans": 4, "traces": 1}

    rows = AtlasStore(ws).search_facts("property search")
    assert [row["fact_id"] for row in rows]
    assert "fact.api.property_search.endpoint" in {row["fact_id"] for row in rows}


def test_parse_citations_prefers_atlas_block() -> None:
    parsed = parse_citations(
        '<atlas_citations>{"citations":[{"fact_id":"fact.api.property_search.endpoint"}]}</atlas_citations>'
    )
    assert parsed["format"] == "atlas_citations"
    assert parsed["fact_ids"] == ["fact.api.property_search.endpoint"]


def test_cli_accepts_nested_atlas_index(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "atlas",
            "index",
            "--atlas",
            str(ATLAS),
            "--ngk-dir",
            str(tmp_path / ".ngk"),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(result.stdout) == {"facts": 3, "evidence": 4, "spans": 4, "traces": 1}
