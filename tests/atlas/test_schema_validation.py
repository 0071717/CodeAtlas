"""Phase 00/01 strict validation acceptance tests."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / "atlas" / "tools"
VALIDATOR = TOOLS / "validate_artifacts.py"


def artifact_envelope(stem="x", kind="artifact"):
    return {"schema_version":"1","artifact_id":f"codeatlas.{stem.replace('/','.')}","artifact_kind":kind,"generated_at":"2026-01-01T00:00:00Z","generator":{"id":"test","version":"1","command":"pytest"},"source":{"repo":"r","source_commit":"a"*40,"dirty_worktree":False,"file_manifest_hash":"b"*64},"validation":{"status":"ok","validated_at":"2026-01-01T00:00:00Z","validator":"pytest","errors":[],"warnings":[]},"data":{"payload_hash":"c"*64,"root_keys":[],"data_keys":[]}}


def provenance():
    return {"schema_version":"1","generated_at":"2026-01-01T00:00:00Z","generator":{"id":"test","version":"1","command":"pytest"},"input_artifact_sha256":"d"*64,"source_manifest_sha256":"e"*64}


def evidence():
    return {"type":"code","evidence_id":"ev.test","evidence_kind":"source_span","source_commit":"a"*40,"repo":"r","file_path":"f.py","file_hash":"f"*64,"span":{"start_line":1,"end_line":2,"start_col":1,"end_col":1},"snippet_hash":"1"*64,"extractor":{"id":"codeatlas.v2.test","version":"1","kind":"python_ast"},"deterministic":True,"verification_status":"current","commit_sha":"a"*40,"file":"f.py","file_sha256":"f"*64,"line_start":1,"line_end":2,"snippet_sha256":"1"*64,"extractor_version":"1"}


def write(atlas: Path, stem: str, doc: dict, kind: str):
    doc = {**doc, "artifact_envelope": artifact_envelope(stem, kind)}
    path = atlas / f"{stem}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")


def build(atlas: Path):
    rec = {"id":"x","state":"verified","confidence":"high","needs_review":False,"evidence":[evidence()],"provenance":provenance()}
    write(atlas,"source/snapshot",{"generated_at":"g","repositories":[{"id":"r"}]},"source_snapshot")
    write(atlas,"index/file-index",{"generated_at":"g","files":[{"id":"f","repo":"r","path":"f.py","language":"python","classification":"source","line_count":2,"size_bytes":10,"sha256":"f"*64}]},"file_index")
    write(atlas,"index/symbol-index",{"generated_at":"g","symbols":[rec]},"symbol_index")
    write(atlas,"graph/nodes",{"generated_at":"g","nodes":[{**rec,"id":"node.x","type":"symbol","repo":"r","file":"f.py","name":"s"}]},"graph_nodes")
    write(atlas,"graph/edges",{"generated_at":"g","edges":[{**rec,"id":"edge.x","source":"node.x","target":"node.x","type":"CALLS"}]},"graph_edges")
    write(atlas,"facts/technical-facts",{"generated_at":"g","technical_facts":[{**rec,"id":"fact.x","domain":"d","source_type":"endpoint","statement":"stmt"}]},"technical_facts")


def load_module():
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))
    spec = importlib.util.spec_from_file_location("validate_artifacts_under_test", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run(atlas: Path, strict=False):
    m = load_module()
    findings, count = m.run_validation(atlas, strict=strict)
    return m.compute_exit(findings, strict=strict), {"findings":findings,"count":count,"types":{f.get("type") for f in findings},"errors":[f for f in findings if f.get("severity")=="error"],"warnings":[f for f in findings if f.get("severity")=="warning"]}


def test_valid_atlas_passes_strict_and_non_strict(tmp_path):
    build(tmp_path)
    assert run(tmp_path)[0] == 0
    code, report = run(tmp_path, strict=True)
    assert code == 0, report
    assert not report["errors"]


def test_missing_required_record_field_and_bad_enum_fail(tmp_path):
    build(tmp_path)
    facts = json.loads((tmp_path/"facts/technical-facts.json").read_text())
    facts["technical_facts"][0].pop("state")
    (tmp_path/"facts/technical-facts.json").write_text(json.dumps(facts))
    assert "schema_missing_required" in run(tmp_path)[1]["types"]
    facts["technical_facts"][0]["state"] = "verified"
    facts["technical_facts"][0]["confidence"] = "extremely-high"
    (tmp_path/"facts/technical-facts.json").write_text(json.dumps(facts))
    assert "schema_invalid_enum" in run(tmp_path)[1]["types"]


def test_missing_artifact_envelope_warns_non_strict_but_fails_strict(tmp_path):
    build(tmp_path)
    facts = json.loads((tmp_path/"facts/technical-facts.json").read_text())
    facts.pop("artifact_envelope")
    (tmp_path/"facts/technical-facts.json").write_text(json.dumps(facts))
    loose_code, loose = run(tmp_path)
    assert loose_code == 0 and "missing_artifact_envelope" in loose["types"]
    strict_code, strict = run(tmp_path, strict=True)
    assert strict_code != 0 and "missing_artifact_envelope" in strict["types"]


def test_legacy_evidence_and_broken_edges_fail(tmp_path):
    build(tmp_path)
    facts = json.loads((tmp_path/"facts/technical-facts.json").read_text())
    facts["technical_facts"][0]["evidence"][0] = {"type":"code","repo":"r","file":"f.py","line_start":1,"line_end":2,"commit_sha":"a"*40,"file_sha256":"f"*64,"snippet_sha256":"1"*64,"extractor":"legacy","extractor_version":"1","deterministic":True,"verification_status":"current"}
    (tmp_path/"facts/technical-facts.json").write_text(json.dumps(facts))
    types = run(tmp_path)[1]["types"]
    assert "evidence_missing_envelope_field" in types and "evidence_invalid_extractor" in types
    build(tmp_path)
    edges = json.loads((tmp_path/"graph/edges.json").read_text())
    edges["edges"][0]["target"] = "missing"
    (tmp_path/"graph/edges.json").write_text(json.dumps(edges))
    assert "edge_broken_target" in run(tmp_path)[1]["types"]


def test_empty_missing_and_schema_engine_fail_closed(tmp_path, monkeypatch):
    atlas = tmp_path/"atlas"; atlas.mkdir()
    assert run(atlas)[0] == 0
    assert run(atlas, strict=True)[0] != 0
    assert "missing_atlas_directory" in run(tmp_path/"missing")[1]["types"]
    build(tmp_path)
    m = load_module()
    monkeypatch.setattr(m, "load_validator_class", lambda: None)
    findings, _ = m.run_validation(tmp_path, strict=True)
    assert "schema_engine_unavailable" in {f.get("type") for f in findings}
    assert m.compute_exit(findings, strict=True) != 0
