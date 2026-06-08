from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / "atlas" / "tools"
CONTRACT = TOOLS / "codeatlas_artifact_contract.py"


def load_contract():
    spec = importlib.util.spec_from_file_location("artifact_contract_under_test", CONTRACT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_normalize_evidence_item_adds_phase01_fields_and_legacy_aliases():
    c = load_contract()
    ev = c.normalize_evidence_item(
        {
            "type": "code",
            "repo": "r",
            "file": "app/main.py",
            "line_start": 2,
            "line_end": 5,
            "commit_sha": "a" * 40,
            "file_sha256": "b" * 64,
            "snippet_sha256": "c" * 64,
        },
        default_extractor_id="codeatlas.v2.python",
        default_extractor_version="1+abc",
        default_extractor_kind="python_ast",
    )

    assert ev["evidence_id"].startswith("ev.")
    assert ev["evidence_kind"] == "source_span"
    assert ev["source_commit"] == "a" * 40
    assert ev["file_path"] == "app/main.py"
    assert ev["file_hash"] == "b" * 64
    assert ev["span"] == {"start_line": 2, "end_line": 5, "start_col": 1, "end_col": 1}
    assert ev["snippet_hash"] == "c" * 64
    assert ev["extractor"] == {"id": "codeatlas.v2.python", "version": "1+abc", "kind": "python_ast"}
    assert ev["file"] == ev["file_path"]
    assert ev["file_sha256"] == ev["file_hash"]
    assert ev["commit_sha"] == ev["source_commit"]
    assert ev["snippet_sha256"] == ev["snippet_hash"]
    assert ev["extractor_version"] == "1+abc"


def test_attach_artifact_envelope_keeps_payload_and_records_validation():
    c = load_contract()
    doc = c.attach_artifact_envelope(
        {"generated_at": "2026-01-01T00:00:00Z", "records": [{"id": "x"}]},
        stem="facts/demo",
        artifact_kind="technical_facts",
        generator_id="test-generator",
        generator_version="1",
        generator_command="test command",
        source={"repo": "r", "source_commit": "a" * 40, "dirty_worktree": False, "file_manifest_hash": "b" * 64},
        validation=c.validation_descriptor(status="ok", validator="test"),
        data_keys=["records"],
    )

    assert doc["records"] == [{"id": "x"}]
    envelope = doc["artifact_envelope"]
    assert envelope["schema_version"] == "1"
    assert envelope["artifact_id"] == "codeatlas.facts.demo"
    assert envelope["artifact_kind"] == "technical_facts"
    assert envelope["generator"]["id"] == "test-generator"
    assert envelope["generator"]["command"] == "test command"
    assert envelope["source"]["file_manifest_hash"] == "b" * 64
    assert envelope["validation"]["status"] == "ok"
    assert envelope["data"]["data_keys"] == ["records"]
    assert len(envelope["data"]["payload_hash"]) == 64
