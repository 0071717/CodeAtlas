from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from ngk_framework.base import Workspace
from ngk_orchestrator.kiro.headless_runner import HeadlessRunner
from ngk_orchestrator.models import base_agent_result, validate_agent_result
from ngk_orchestrator.storage import OrchestrationStore
from ngk_orchestrator.event_log import EventLog
from ngk_orchestrator.engine.conflict_detector import detect_conflicts
from ngk_orchestrator.hooks_common import guard_event


def test_agent_result_supported_requires_fact_id():
    payload = base_agent_result("t1", "frontend", findings=[{"finding_id":"f1","severity":"high","title":"x","claim":"x","support":"supported","confidence":"high","fact_ids":[],"evidence":[],"recommended_tests":[],"risk_tags":[]}])
    result = validate_agent_result(payload)
    assert not result.valid
    assert any("requires at least one fact_id" in e for e in result.errors)


def test_storage_and_event_log(tmp_path: Path):
    ws = Workspace(tmp_path)
    store = OrchestrationStore(ws)
    orch = store.create("init-test", "request")
    assert (store.path(orch["orchestration_id"]) / "tasks").is_dir()
    event = EventLog(ws, orch["orchestration_id"]).append("unit")
    assert event["event_type"] == "unit"
    assert store.latest_id() == orch["orchestration_id"]


def test_runner_command_least_privilege(tmp_path: Path):
    ws = Workspace(tmp_path)
    cmd = HeadlessRunner(ws).build_command(agent_name="ngk-test", context_pack_path="ctx.md", task_id="t1")
    assert "--trust-tools=read,grep" in cmd
    assert "--trust-all-tools" not in cmd


def test_pre_tool_guard_blocks_and_allows():
    assert guard_event({"tool":"shell", "command":"ngk tool fact --id fact.x --json"})[0]
    assert not guard_event({"tool":"shell", "command":"git commit -m x"})[0]
    assert not guard_event({"tool":"read", "path":".env"})[0]


def test_conflict_detector_no_impact_vs_issue():
    a = base_agent_result("a", "p1", findings=[{"finding_id":"a1","severity":"info","title":"none","claim":"no impact","support":"inferred","confidence":"low","fact_ids":["fact.x"],"evidence":[],"recommended_tests":[],"risk_tags":[]}])
    b = base_agent_result("b", "p2", findings=[{"finding_id":"b1","severity":"high","title":"issue","claim":"issue","support":"supported","confidence":"high","fact_ids":["fact.x"],"evidence":[],"recommended_tests":[],"risk_tags":[]}])
    assert detect_conflicts([a, b])["conflicts"]
