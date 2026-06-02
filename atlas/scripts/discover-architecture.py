#!/usr/bin/env python3
"""
Runs Kiro architecture discovery before CodeAtlas extraction.

This launches fresh Kiro sessions for:
1. architecture discovery
2. architecture verification

It creates editable architecture briefs and updates .kiro/steering.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROMPTS = ROOT / "atlas" / "prompts"
LOG_DIR = ROOT / "atlas" / "logs" / f"architecture-{dt.datetime.now().strftime('%Y-%m-%d_%H%M%S')}"

PHASES = [
    ("00a-architecture-discovery.md", "architecture-discovery.log"),
    ("00b-architecture-verification.md", "architecture-verification.log"),
]

def run_phase(prompt_file: str, log_name: str, agent: str, extra_args: str, retries: int):
    prompt_path = PROMPTS / prompt_file
    if not prompt_path.exists():
        raise SystemExit(f"Missing prompt: {prompt_path}")

    prompt = prompt_path.read_text(encoding="utf-8")
    default_args = os.environ.get("KIRO_DEFAULT_ARGS", "--no-interactive --trust-all-tools")
    agent = os.environ.get("KIRO_AGENT", agent)

    cmd = ["kiro-cli", "chat", "--agent", agent]
    if default_args.strip():
        cmd.extend(shlex.split(default_args))
    if extra_args.strip():
        cmd.extend(shlex.split(extra_args))
    cmd.append(prompt)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / log_name

    for attempt in range(1, retries + 2):
        print(f"\n=== Architecture phase: {prompt_file} | attempt {attempt}/{retries + 1} ===")
        print(f"Agent: {agent}")
        print(f"Log: {log_path}")
        print("Command:", " ".join(shlex.quote(x) for x in cmd[:-1]), "<PROMPT>")

        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"\n\n===== {dt.datetime.now().isoformat()} {prompt_file} attempt={attempt} =====\n")
            proc = subprocess.Popen(
                cmd,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                print(line, end="")
                f.write(line)
            rc = proc.wait()

        if rc == 0:
            return

        print(f"Phase failed with exit code {rc}")

    raise SystemExit(f"Architecture phase failed: {prompt_file}")

def validate_outputs():
    required = [
        "atlas/architecture-discovery/backend-architecture-draft.md",
        "atlas/architecture-discovery/frontend-architecture-draft.md",
        "atlas/architecture-discovery/cross-repo-architecture-draft.md",
        "atlas/architecture-discovery/architecture-evidence.yaml",
        "atlas/architecture-discovery/architecture-open-questions.md",
        "atlas/architecture-discovery/backend-architecture-verified.md",
        "atlas/architecture-discovery/frontend-architecture-verified.md",
        "atlas/architecture-discovery/cross-repo-architecture-verified.md",
        "atlas/architecture-discovery/extraction-traversal-guide.md",
        "atlas/architecture-discovery/human-review-checklist.md",
    ]

    missing = []
    for rel in required:
        if not (ROOT / rel).exists():
            missing.append(rel)

    if missing:
        print("Missing architecture outputs:")
        for item in missing:
            print(f" - {item}")
        raise SystemExit(1)

    print("\nArchitecture discovery outputs created successfully.")
    print("Review this first:")
    print("atlas/architecture-discovery/human-review-checklist.md")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", default="atlas-cartographer", help="Kiro agent to use unless KIRO_AGENT is set.")
    parser.add_argument("--kiro-extra-args", default=os.environ.get("KIRO_EXTRA_ARGS", ""))
    parser.add_argument("--retries", type=int, default=1)
    args = parser.parse_args()

    for prompt_file, log_name in PHASES:
        run_phase(prompt_file, log_name, args.agent, args.kiro_extra_args, args.retries)

    validate_outputs()

if __name__ == "__main__":
    main()
