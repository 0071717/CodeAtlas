from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from ngk_framework.cli import parse_citations
from ngk_test_helpers import ATLAS, EXAMPLE, ROOT, add_property_hub_graph, write_answer_session

def test_ctx_build_creates_evidence_backed_context_pack_and_explain(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    add_property_hub_graph(project)
    base = ["--atlas", str(project / ".atlas"), "--ngk-dir", str(tmp_path / ".ngk")]
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "ctx",
            "build",
            "ask",
            "How does property search flow from UI to API?",
            *base,
            "--limit",
            "5",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    context_path = Path(result.stdout.strip())
    text = context_path.read_text(encoding="utf-8")
    assert "## User task" in text
    assert "## Atlas drift status" in text
    assert "## Selected facts" in text
    assert "fact.api.property_search.endpoint" in text
    assert "api/app/routers/property.py:8-14" in text
    assert "## Selected traces" in text
    assert "trace.property_search.ui_to_api" in text
    assert "## Related tests" in text
    assert "## Known gaps" in text
    assert "## Strict Kiro citation rules" in text
    assert "<atlas_citations>" in text

    payload = json.loads((context_path.parent / "context-pack.json").read_text(encoding="utf-8"))
    assert payload["drift"]["status"] in {"clean", "drift"}
    assert payload["facts"][0]["selection_reason"]
    assert payload["facts"][0]["evidence"]
    assert payload["traces"]

    explain = subprocess.run(
        [sys.executable, str(ROOT / "atlas" / "tools" / "ngk_cli.py"), "ctx", "explain", "latest", *base, "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    explanation = json.loads(explain.stdout)
    assert explanation["facts"]
    assert explanation["traces"]
    assert any("matched user task" in fact["reason"] for fact in explanation["facts"])


def test_ask_no_agent_writes_context_pack_without_kiro(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "ask",
            "What endpoint powers property search?",
            "--atlas",
            str(ATLAS),
            "--ngk-dir",
            str(tmp_path / ".ngk"),
            "--no-agent",
            "--limit",
            "3",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    prefix = "Context pack: "
    assert prefix in result.stdout
    context_path = Path(result.stdout.strip().split(prefix, 1)[1])
    assert context_path.exists()
    text = context_path.read_text(encoding="utf-8")
    assert "The backend exposes GET /properties/search" in text
    assert "Required <atlas_citations> JSON schema" in text
    assert not (context_path.parent / "kiro-output.raw.md").exists()


def test_verify_answer_accepts_good_block_and_preserves_not_confirmed(tmp_path: Path) -> None:
    ngk_dir = tmp_path / ".ngk"
    write_answer_session(
        ngk_dir,
        "good",
        """
The backend exposes the property search endpoint.
<atlas_citations>{
  "claims": [
    {"claim_id": "claim.1", "text": "Property search has an API endpoint.", "support": "supported", "fact_ids": ["fact.api.property_search.endpoint"]}
  ],
  "citations": [{"fact_id": "fact.api.property_search.endpoint", "used_for_claims": ["claim.1"]}],
  "not_confirmed": [{"claim_id": "claim.2", "text": "Latency is under 10ms.", "reason": "No Atlas fact confirms latency."}]
}</atlas_citations>
""",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "verify-answer",
            "latest",
            "--atlas",
            str(ATLAS),
            "--ngk-dir",
            str(ngk_dir),
            "--json",
            "--strict",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    audit = json.loads(result.stdout)
    assert audit["status"] == "passed"
    assert audit["resolved_fact_ids"] == ["fact.api.property_search.endpoint"]
    assert audit["not_confirmed"][0]["claim_id"] == "claim.2"
    assert audit["unsupported_claims"] == []


def test_verify_answer_reports_missing_and_hallucinated_citations(tmp_path: Path) -> None:
    ngk_dir = tmp_path / ".ngk"
    write_answer_session(
        ngk_dir,
        "bad",
        '<atlas_citations>{"claims":[{"claim_id":"claim.1","text":"A hallucinated fact supports this.","support":"supported","fact_ids":["fact.missing.hallucinated"]}],"citations":[{"fact_id":"fact.missing.hallucinated"}],"not_confirmed":[]}</atlas_citations>',
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "verify-answer",
            "bad",
            "--atlas",
            str(ATLAS),
            "--ngk-dir",
            str(ngk_dir),
            "--json",
            "--strict",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 6
    audit = json.loads(result.stdout)
    assert audit["status"] == "failed"
    assert audit["missing_fact_ids"] == ["fact.missing.hallucinated"]
    assert audit["unsupported_claims"][0]["claim_id"] == "claim.1"


def test_verify_answer_supports_inline_and_fallback_fact_scanning(tmp_path: Path) -> None:
    inline = parse_citations("The endpoint exists [fact.api.property_search.endpoint].")
    fallback = parse_citations("The endpoint exists fact.api.property_search.endpoint.")
    assert inline["format"] == "inline_brackets"
    assert inline["fact_ids"] == ["fact.api.property_search.endpoint"]
    assert fallback["format"] == "fallback_scan"
    assert fallback["fact_ids"] == ["fact.api.property_search.endpoint"]


def test_verify_answer_reports_stale_cited_source(tmp_path: Path) -> None:
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project)
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=project, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-c", "user.email=ngk@example.com", "-c", "user.name=ngk", "commit", "-m", "baseline"],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    route = project / "api" / "app" / "routers" / "property.py"
    route.write_text(route.read_text(encoding="utf-8") + "\n# stale\n", encoding="utf-8")
    ngk_dir = tmp_path / ".ngk"
    write_answer_session(
        ngk_dir,
        "stale",
        '<atlas_citations>{"claims":[{"claim_id":"claim.1","text":"The route exists.","support":"supported","fact_ids":["fact.api.property_search.endpoint"]}],"citations":[{"fact_id":"fact.api.property_search.endpoint"}],"not_confirmed":[]}</atlas_citations>',
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "atlas" / "tools" / "ngk_cli.py"),
            "verify-answer",
            "stale",
            "--atlas",
            str(project / ".atlas"),
            "--ngk-dir",
            str(ngk_dir),
            "--json",
            "--strict",
        ],
        cwd=project,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 6
    audit = json.loads(result.stdout)
    assert audit["stale_fact_ids"] == ["fact.api.property_search.endpoint"]
    assert "cited facts have stale sources" in audit["unsupported_claims"][0]["reasons"][-1]
