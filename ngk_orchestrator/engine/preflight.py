from __future__ import annotations

import subprocess
from typing import Any

from ngk_framework.base import Workspace
from ngk_framework.drift import evaluate_drift


def _git(args:list[str], cwd) -> tuple[int,str]:
    try:
        p=subprocess.run(['git',*args],cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10)
        return p.returncode,p.stdout.strip()
    except Exception:
        return 1,''

def changed_files(ws: Workspace) -> list[str]:
    code,out=_git(['diff','--name-only','HEAD'], ws.root)
    files=[x for x in out.splitlines() if x]
    code2,out2=_git(['ls-files','--others','--exclude-standard'], ws.root)
    return sorted(set(files+[x for x in out2.splitlines() if x]))

def run_preflight(ws: Workspace, *, strict: bool=False) -> dict[str, Any]:
    _,commit=_git(['rev-parse','HEAD'], ws.root)
    files=changed_files(ws)
    drift=evaluate_drift(ws) if ws.atlas.exists() else {"status":"warning","issues":[],"capability_gap":"atlas index missing"}
    status='ok'
    errors=[]
    if not ws.atlas.exists():
        status='error' if strict else 'warning'; errors.append('Atlas index missing')
    if strict and drift.get('status') == 'failed':
        status='error'; errors.append('stale Atlas evidence')
    return {"schema_version":"1","status":status,"errors":errors,"git_commit":commit,"dirty_files":files,"changed_files":files,"drift":drift}
