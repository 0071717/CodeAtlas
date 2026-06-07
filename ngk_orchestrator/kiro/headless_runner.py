from __future__ import annotations

import os
import shlex
import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from ngk_framework.base import Workspace

from .capability_probe import load_kiro_config


@dataclass
class HeadlessRunResult:
    command: list[str]
    stdout: str
    stderr: str
    exit_code: int
    duration_seconds: float
    timed_out: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HeadlessRunner:
    def __init__(self, ws: Workspace) -> None:
        self.ws = ws
        self.config = load_kiro_config(ws)["kiro"]

    def build_command(self, *, agent_name: str, context_pack_path: str | Path, task_id: str) -> list[str]:
        command = [str(self.config.get("command") or "kiro-cli")]
        command.extend(str(x) for x in self.config.get("chat_args", []))
        style = str(self.config.get("agent_arg_style") or "--agent {agent_name}")
        if "{agent_name}" in style:
            rendered = style.format(agent_name=agent_name)
            command.extend(shlex.split(rendered))
        trust = str(self.config.get("default_trust_tools") or "read,grep")
        if trust and "--trust-all-tools" not in trust:
            command.append(f"--trust-tools={trust}")
        command.extend(["--context", str(context_pack_path), "--task-id", task_id])
        return command

    def run(self, *, agent_name: str, context_pack_path: str | Path, task_id: str, env: dict[str, str] | None = None, timeout: int | None = None) -> HeadlessRunResult:
        cmd = self.build_command(agent_name=agent_name, context_pack_path=context_pack_path, task_id=task_id)
        merged_env = {**os.environ, **(env or {})}
        seconds = timeout or int(self.config.get("timeout_seconds") or 240)
        start = time.monotonic()
        try:
            proc = subprocess.run(cmd, cwd=self.ws.root, env=merged_env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=seconds)
            return HeadlessRunResult(cmd, proc.stdout, proc.stderr, proc.returncode, round(time.monotonic() - start, 3), False)
        except subprocess.TimeoutExpired as exc:
            return HeadlessRunResult(cmd, exc.stdout or "", exc.stderr or "", 124, round(time.monotonic() - start, 3), True)
        except FileNotFoundError as exc:
            return HeadlessRunResult(cmd, "", str(exc), 127, round(time.monotonic() - start, 3), False)
