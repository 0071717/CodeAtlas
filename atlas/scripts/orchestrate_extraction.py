#!/usr/bin/env python3
"""
Hands-off Kiro CodeAtlas extraction orchestrator.

This script launches a fresh `kiro-cli chat --agent ...` process for every phase.
It is designed to be run from the root of this atlas-kit repo.

Default flow:
1. Repo health check
2. Repository census
3. Domain map
4. Auto-select a pilot domain
5. Run pilot domain end-to-end
6. Validate pilot output
7. If --auto-scale is supplied, run remaining domains
8. Produce global validation summary

Important:
- This script does not require you to manually open Kiro sessions.
- It assumes your Kiro CLI supports: `kiro-cli chat --agent <agent>`.
- If your CLI supports extra args such as model selection, pass them through:
    export KIRO_EXTRA_ARGS="--model claude-opus-4.6"
  or:
    python3 ... --kiro-extra-args "--model claude-opus-4.6"

If your Kiro model can only be switched interactively via /model, set Opus as the
default in Kiro once, then run this script.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, Optional

try:
    import yaml
except ImportError:
    print("Missing dependency: pyyaml. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[2]
EXTRACTION_DIR = ROOT / "atlas"
PROMPTS_DIR = EXTRACTION_DIR / "prompts"
GLOBAL_DIR = EXTRACTION_DIR / "global"
DOMAINS_DIR = EXTRACTION_DIR / "domains"
LOG_DIR = EXTRACTION_DIR / "logs" / dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")

GLOBAL_PHASES = [
    ("00a-architecture-discovery.md", "atlas-cartographer", "00a-architecture-discovery.log"),
    ("00b-architecture-verification.md", "atlas-cartographer", "00b-architecture-verification.log"),
    ("00-repo-health-check.md", "atlas-cartographer", "00-repo-health-check.log"),
    ("01-repository-census.md", "atlas-cartographer", "01-repository-census.log"),
    ("02-domain-map.md", "atlas-cartographer", "02-domain-map.log"),
]

DOMAIN_PHASES = [
    ("03-domain-scope.md", "domain-scout"),
    ("04-backend-technical-rules.md", "domain-scout"),
    ("05-frontend-technical-rules.md", "domain-scout"),
    ("06-contract-mapping.md", "domain-scout"),
    ("07-business-rules.md", "domain-scout"),
    ("08-user-stories.md", "domain-scout"),
    ("09-epics-hlrs.md", "domain-scout"),
    ("10-contradictions-dead-code.md", "rift-hunter"),
    ("11-update-kiro-steering.md", "memory-smith"),
    ("12-review-pack.md", "domain-scout"),
]

REQUIRED_DOMAIN_FILES = [
    "00-domain-scope.yaml",
    "01-backend-inventory.yaml",
    "02-frontend-inventory.yaml",
    "03-code-references.json",
    "04-technical-rules-backend.yaml",
    "04-technical-rules-frontend.yaml",
    "05-contract-mapping.yaml",
    "06-business-rules.yaml",
    "07-user-stories.yaml",
    "08-epics.yaml",
    "09-high-level-requirements.yaml",
    "10-contradictions.yaml",
    "11-dead-code-candidates.yaml",
    "12-review-notes.md",
]

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def log(msg: str) -> None:
    print(msg, flush=True)

def shell_join(parts: Iterable[str]) -> str:
    return " ".join(shlex.quote(p) for p in parts)

def check_kiro_available() -> None:
    try:
        subprocess.run(["kiro-cli", "--help"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except FileNotFoundError:
        raise SystemExit("kiro-cli not found on PATH. Install/configure Kiro CLI first.")

def build_command(agent: str, prompt: str, extra_args: str) -> list[str]:
    cmd = ["kiro-cli", "chat", "--agent", agent]

    # Some Kiro setups support --no-interactive / --trust-tools; some may not.
    # These are enabled by default because this orchestrator is intended to be headless.
    default_args = os.environ.get("KIRO_DEFAULT_ARGS", "--no-interactive --trust-tools read,write,shell")
    if default_args.strip():
        cmd.extend(shlex.split(default_args))

    if extra_args.strip():
        cmd.extend(shlex.split(extra_args))

    cmd.append(prompt)
    return cmd

def run_kiro_phase(
    *,
    phase_name: str,
    agent: str,
    prompt: str,
    log_file: Path,
    extra_args: str,
    retries: int,
    retry_delay_seconds: int,
) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_command(agent, prompt, extra_args)

    for attempt in range(1, retries + 2):
        log(f"\n==================================================")
        log(f"Phase: {phase_name}")
        log(f"Agent: {agent}")
        log(f"Attempt: {attempt}/{retries + 1}")
        log(f"Log: {log_file}")
        log(f"Command: {shell_join(cmd[:-1])} <PROMPT>")
        log(f"==================================================\n")

        with log_file.open("a", encoding="utf-8") as f:
            f.write(f"\n\n===== {dt.datetime.now().isoformat()} phase={phase_name} attempt={attempt} =====\n")
            f.write(f"Command: {shell_join(cmd[:-1])} <PROMPT>\n\n")
            process = subprocess.Popen(
                cmd,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            assert process.stdout is not None
            for line in process.stdout:
                print(line, end="")
                f.write(line)

            rc = process.wait()

        if rc == 0:
            log(f"Phase completed: {phase_name}")
            return

        log(f"Phase failed with exit code {rc}: {phase_name}")

        if attempt <= retries:
            log(f"Retrying in {retry_delay_seconds} seconds...")
            time.sleep(retry_delay_seconds)

    raise SystemExit(f"Phase failed after retries: {phase_name}. See {log_file}")

def run_prompt_file(prompt_file: str, agent: str, domain_id: Optional[str], extra_args: str, retries: int) -> None:
    path = PROMPTS_DIR / prompt_file
    if not path.exists():
        raise SystemExit(f"Missing prompt file: {path}")

    prompt = read_text(path)
    if domain_id:
        prompt = prompt.replace("<DOMAIN_ID>", domain_id)

    log_name = prompt_file.replace(".md", ".log")
    if domain_id:
        log_name = f"{domain_id}-{log_name}"

    run_kiro_phase(
        phase_name=f"{domain_id + ' ' if domain_id else ''}{prompt_file}",
        agent=agent,
        prompt=prompt,
        log_file=LOG_DIR / log_name,
        extra_args=extra_args,
        retries=retries,
        retry_delay_seconds=15,
    )

def validate_global() -> bool:
    required = [
        ROOT / "atlas" / "architecture-discovery" / "extraction-traversal-guide.md",
        GLOBAL_DIR / "repo-health-report.md",
        GLOBAL_DIR / "repo-health.json",
        GLOBAL_DIR / "frontend-inventory.yaml",
        GLOBAL_DIR / "backend-inventory.yaml",
        GLOBAL_DIR / "endpoint-index.yaml",
        GLOBAL_DIR / "ui-route-index.yaml",
        GLOBAL_DIR / "initial-domain-candidates.yaml",
        GLOBAL_DIR / "domain-map.yaml",
    ]

    ok = True
    for path in required:
        if not path.exists():
            log(f"[VALIDATION] Missing global file: {path}")
            ok = False

    if (GLOBAL_DIR / "domain-map.yaml").exists():
        try:
            data = load_yaml(GLOBAL_DIR / "domain-map.yaml")
            if not data.get("domains"):
                log("[VALIDATION] domain-map.yaml has no domains")
                ok = False
        except Exception as exc:
            log(f"[VALIDATION] Invalid domain-map.yaml: {exc}")
            ok = False

    return ok

def validate_domain(domain_id: str) -> bool:
    domain_dir = DOMAINS_DIR / domain_id
    ok = True

    if not domain_dir.exists():
        log(f"[VALIDATION] Missing domain dir: {domain_dir}")
        return False

    for filename in REQUIRED_DOMAIN_FILES:
        path = domain_dir / filename
        if not path.exists():
            log(f"[VALIDATION] Missing domain file: {path}")
            ok = False
            continue

        try:
            if filename.endswith((".yaml", ".yml")):
                load_yaml(path)
            elif filename.endswith(".json"):
                json.loads(read_text(path))
        except Exception as exc:
            log(f"[VALIDATION] Invalid {path}: {exc}")
            ok = False

    return ok

def get_domains() -> list[dict]:
    domain_map = GLOBAL_DIR / "domain-map.yaml"
    if not domain_map.exists():
        raise SystemExit("Missing domain-map.yaml. Run global phases first.")

    data = load_yaml(domain_map)
    domains = data.get("domains") or []
    if not isinstance(domains, list):
        raise SystemExit("domain-map.yaml has invalid `domains` shape; expected list.")

    clean = []
    for d in domains:
        if isinstance(d, dict) and d.get("id"):
            clean.append(d)
    return clean

def score_domain_for_pilot(domain: dict) -> tuple[int, str]:
    """
    Lower score = better pilot.
    Prefer domains with both frontend and backend but fewer files/endpoints.
    """
    did = domain.get("id", "")
    frontend = domain.get("frontend") or {}
    backend = domain.get("backend") or {}
    endpoints = backend.get("endpoints") or domain.get("api_endpoints") or []
    routes = frontend.get("routes") or domain.get("ui_routes") or []
    files = []
    for section in [frontend, backend]:
        if isinstance(section, dict):
            files.extend(section.get("files") or [])

    has_both_penalty = 0 if frontend and backend else 50
    size = len(endpoints) * 3 + len(routes) * 2 + len(files)
    auth_penalty = 10 if re.search(r"auth|permission|security|admin", did, re.I) else 0
    cross_penalty = 20 if re.search(r"cross|shared|infrastructure|common", did, re.I) else 0
    return (has_both_penalty + size + auth_penalty + cross_penalty, did)

def select_pilot_domain(domains: list[dict]) -> str:
    if not domains:
        raise SystemExit("No domains found.")
    return sorted(domains, key=score_domain_for_pilot)[0]["id"]

def run_global_phases(extra_args: str, retries: int) -> None:
    for prompt_file, agent, _log_name in GLOBAL_PHASES:
        run_prompt_file(prompt_file, agent, None, extra_args, retries)

    if not validate_global():
        raise SystemExit("Global validation failed. Inspect logs and generated global files.")

def run_domain(domain_id: str, extra_args: str, retries: int) -> None:
    (DOMAINS_DIR / domain_id).mkdir(parents=True, exist_ok=True)
    for prompt_file, agent in DOMAIN_PHASES:
        run_prompt_file(prompt_file, agent, domain_id, extra_args, retries)

    if not validate_domain(domain_id):
        raise SystemExit(f"Domain validation failed for {domain_id}. Inspect logs and domain artifacts.")

def write_run_summary(started_at: dt.datetime, completed_domains: list[str], pilot_domain: Optional[str]) -> None:
    summary = {
        "started_at": started_at.isoformat(),
        "finished_at": dt.datetime.now().isoformat(),
        "log_dir": str(LOG_DIR.relative_to(ROOT)),
        "pilot_domain": pilot_domain,
        "completed_domains": completed_domains,
    }
    write_text(LOG_DIR / "run-summary.json", json.dumps(summary, indent=2))
    write_text(
        LOG_DIR / "run-summary.md",
        "# Extraction Run Summary\n\n"
        f"- Started: {summary['started_at']}\n"
        f"- Finished: {summary['finished_at']}\n"
        f"- Pilot domain: {pilot_domain or 'N/A'}\n"
        f"- Completed domains: {', '.join(completed_domains) if completed_domains else 'None'}\n"
        f"- Logs: `{summary['log_dir']}`\n",
    )

def main() -> None:
    parser = argparse.ArgumentParser(description="Hands-off Kiro CodeAtlas extraction orchestrator.")
    parser.add_argument("--skip-global", action="store_true", help="Skip repo health, census, and domain-map phases.")
    parser.add_argument("--pilot-domain", help="Domain id to use as pilot. If omitted, one is selected automatically.")
    parser.add_argument("--only-domain", help="Run exactly one domain and stop.")
    parser.add_argument("--auto-scale", action="store_true", help="After pilot passes, run all remaining domains.")
    parser.add_argument("--no-pilot", action="store_true", help="Run all domains directly. Not recommended.")
    parser.add_argument("--retries", type=int, default=1, help="Retry failed Kiro phases this many times.")
    parser.add_argument("--kiro-extra-args", default=os.environ.get("KIRO_EXTRA_ARGS", ""), help="Extra args passed to kiro-cli chat.")
    args = parser.parse_args()

    started_at = dt.datetime.now()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    completed_domains: list[str] = []
    pilot_domain: Optional[str] = None

    check_kiro_available()

    if not args.skip_global:
        run_global_phases(args.kiro_extra_args, args.retries)
    elif not validate_global():
        raise SystemExit("Global files are incomplete. Remove --skip-global or fix global outputs.")

    domains = get_domains()

    if args.only_domain:
        run_domain(args.only_domain, args.kiro_extra_args, args.retries)
        completed_domains.append(args.only_domain)
        write_run_summary(started_at, completed_domains, args.only_domain)
        return

    if args.no_pilot:
        for d in domains:
            run_domain(d["id"], args.kiro_extra_args, args.retries)
            completed_domains.append(d["id"])
        write_run_summary(started_at, completed_domains, None)
        return

    pilot_domain = args.pilot_domain or select_pilot_domain(domains)
    log(f"Selected pilot domain: {pilot_domain}")

    run_domain(pilot_domain, args.kiro_extra_args, args.retries)
    completed_domains.append(pilot_domain)

    if args.auto_scale:
        for d in domains:
            domain_id = d["id"]
            if domain_id == pilot_domain:
                continue
            run_domain(domain_id, args.kiro_extra_args, args.retries)
            completed_domains.append(domain_id)
    else:
        log("\nPilot completed successfully.")
        log("Review the pilot output, then rerun with --auto-scale to process all domains.")
        log(f"Pilot review pack: atlas/domains/{pilot_domain}/12-review-notes.md")

    write_run_summary(started_at, completed_domains, pilot_domain)

if __name__ == "__main__":
    main()
