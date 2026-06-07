from __future__ import annotations
import json, os, re, sys
from pathlib import Path

SECRET_PATTERNS=['.env','private_key','id_rsa','secret','token']
DENIED_SHELL=['git commit','git push','rm -rf','npm install','pip install','ngk orchestrate','ngk delegate','kiro']
ALLOWED_NGK_TOOL_PREFIXES=['ngk tool sources','ngk tool fact','ngk tool trace','ngk tool impact','ngk tool tests','ngk tool contract check','ngk tool contract boundary','ngk tool drift','ngk tool verify-result','ngk tool context']
UNSAFE_META=re.compile(r'[;&|`$<>]')

def read_event():
    try: return json.loads(sys.stdin.read() or '{}')
    except Exception: return {}

def event_command(ev):
    return str(ev.get('command') or ev.get('toolInput',{}).get('command') or ev.get('input',{}).get('command') or '')

def event_path(ev):
    return str(ev.get('path') or ev.get('toolInput',{}).get('path') or ev.get('input',{}).get('path') or '')

def redact(s, limit=4000):
    text=str(s or '')[:limit]
    return re.sub(r'(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*\S+', r'\1=<redacted>', text)

def guard_event(ev):
    depth=int(os.environ.get('NGK_AGENT_DEPTH','0')); max_depth=int(os.environ.get('NGK_MAX_AGENT_DEPTH','1'))
    if depth > max_depth: return False,'recursion depth exceeded'
    tool=str(ev.get('tool') or ev.get('toolName') or '').lower()
    path=event_path(ev).lower()
    if path and any(p in path for p in SECRET_PATTERNS): return False,'denied secret path read'
    cmd=event_command(ev).strip()
    read_only=os.environ.get('NGK_TASK_MODE','read_only') == 'read_only'
    if read_only and tool in {'write','edit','create','delete'}: return False,'read-only task attempted write'
    if cmd:
        if any(d in cmd for d in DENIED_SHELL): return False,'denied shell command'
        if UNSAFE_META.search(cmd): return False,'unsafe shell metacharacter'
        if not any(cmd.startswith(p) for p in ALLOWED_NGK_TOOL_PREFIXES): return False,'shell command is not an allowed ngk tool command'
    return True,'ok'
