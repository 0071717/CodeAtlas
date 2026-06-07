#!/usr/bin/env python3
from __future__ import annotations
import json, os, sys
from pathlib import Path
from ngk_orchestrator.hooks_common import read_event, guard_event, redact
from ngk_orchestrator.models import extract_agent_result, validate_agent_result

def main():
    name=Path(__file__).stem
    ev=read_event()
    if name == 'agent_spawn_context':
        print(f"ngk orchestration={os.environ.get('NGK_ORCHESTRATION_ID','')} task={os.environ.get('NGK_TASK_ID','')} profile={os.environ.get('NGK_AGENT_PROFILE','')} depth={os.environ.get('NGK_AGENT_DEPTH','0')}/{os.environ.get('NGK_MAX_AGENT_DEPTH','1')}")
        return 0
    if name == 'user_prompt_context':
        print(f"Use context pack at .ngk/orchestrations/{os.environ.get('NGK_ORCHESTRATION_ID','')}/tasks/{os.environ.get('NGK_TASK_ID','')}/context-pack.md. Do not duplicate injected context.")
        return 0
    if name == 'pre_tool_guard':
        ok,msg=guard_event(ev)
        if not ok:
            print(msg, file=sys.stderr); return 2
        print(json.dumps({'status':'ok','message':msg})); return 0
    if name == 'post_tool_audit':
        oid=os.environ.get('NGK_ORCHESTRATION_ID',''); tid=os.environ.get('NGK_TASK_ID','')
        path=Path('.ngk/orchestrations')/oid/'tasks'/tid/'tool-events.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        row={'event':ev,'stdout':redact(ev.get('stdout','')),'stderr':redact(ev.get('stderr',''))}
        with path.open('a', encoding='utf-8') as fh: fh.write(json.dumps(row, sort_keys=True)+'\n')
        print(json.dumps({'status':'ok','path':str(path)})); return 0
    if name == 'stop_verify_agent_result':
        text=ev.get('response') or ev.get('text') or ev.get('output') or sys.stdin.read()
        payload,errors=extract_agent_result(text)
        if errors:
            print('; '.join(errors), file=sys.stderr); return 2
        res=validate_agent_result(payload)
        if not res.valid:
            print('; '.join(res.errors), file=sys.stderr); return 2
        print(json.dumps({'status':'ok'})); return 0
    return 0
if __name__ == '__main__': raise SystemExit(main())
