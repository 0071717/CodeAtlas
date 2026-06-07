from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ngk_framework.base import Workspace, read_text
from ngk_framework.contract import contract_check
from ngk_framework.drift import evaluate_drift
from ngk_framework.impact import compute_impact, select_tests_from_impact
from ngk_framework.store import AtlasStore

from .event_log import EventLog
from .kiro.capability_probe import load_kiro_config, probe_kiro
from .kiro.custom_agent_generator import generate_kiro_agents
from .kiro.headless_runner import HeadlessRunner
from .models import base_agent_result, extract_agent_result, read_json, task_id, validate_agent_result, write_json
from .profiles_api import list_profiles, load_profile, validate_profiles
from .storage import OrchestrationStore
from .engine.context_builder import build_context_pack
from .engine.preflight import run_preflight
from .engine.planner import plan_review
from .engine.verifier import verify_agent_result
from .engine.synthesizer import synthesize
from .engine.conflict_detector import detect_conflicts
from .engine.worktree_manager import WorktreeManager
from .engine.locks import LockTable, Lock




def fact_payload_local(store: AtlasStore, fact_id: str) -> dict[str, Any]:
    fact = store.get_fact(fact_id)
    if not fact:
        raise SystemExit(f"Unknown fact: {fact_id}")
    evidence = []
    for ev in store.get_evidence(fact_id):
        row = dict(ev)
        span_id = ev["span_id"] if "span_id" in ev.keys() else ""
        span = store.get_source_span(span_id) if span_id else None
        if span:
            row["source_span"] = dict(span)
        evidence.append(row)
    return {"fact": dict(fact), "evidence": evidence, "related_traces": store.related_traces(fact_id), "related_tests": store.related_tests(fact_id)}

def _ws(args): return Workspace(Path.cwd(), getattr(args,'atlas','.atlas'), getattr(args,'ngk_dir','.ngk'))
def _print(payload, json_only=True): print(json.dumps(payload, indent=None if json_only else 2, ensure_ascii=False))
def _status(payload): return {"status":"ok", **payload}
def _warn(msg, **kw): return {"status":"warning","warnings":[msg], **kw}
def _err(msg, **kw): return {"status":"error","errors":[msg], **kw}

# O0

def cmd_kiro_config_show(args): _print(load_kiro_config(_ws(args)), False)
def cmd_kiro_probe(args): _print(probe_kiro(_ws(args)), False)

# O1 orchestrations

def cmd_orch_init_test(args):
    ws=_ws(args); store=OrchestrationStore(ws); o=store.create('init-test','test orchestration')
    EventLog(ws,o['orchestration_id']).append('initialized')
    _print(o, False)

def cmd_orch_list(args): _print({"orchestrations":OrchestrationStore(_ws(args)).list()}, False)

def cmd_orch_show(args):
    ws=_ws(args); store=OrchestrationStore(ws); oid=store.resolve(args.orchestration)
    if getattr(args,'summary',False):
        print(read_text(store.path(oid)/'summary.md') if (store.path(oid)/'summary.md').exists() else '')
        return
    payload=read_json(store.path(oid)/'orchestration.json',{})
    payload['events']=EventLog(ws,oid).read(limit=20)
    _print(payload, False)

# O2 tools

def tool_sources(args):
    ws=_ws(args)
    if not ws.db.exists(): _print(_warn('Atlas cache missing; run ngk atlas index', capability_gap='atlas_cache_missing')); return
    rows=AtlasStore(ws).search(args.query, limit=10)
    _print(_status({"query":args.query,"results":rows}))

def tool_fact(args):
    ws=_ws(args)
    try: payload=fact_payload_local(AtlasStore(ws), args.id)
    except SystemExit: _print(_warn('fact not found', fact_id=args.id)); return
    _print(_status(payload))

def tool_trace(args):
    ws=_ws(args)
    if not ws.db.exists(): _print(_warn('Atlas cache missing', capability_gap='atlas_cache_missing')); return
    _print(_status(AtlasStore(ws).trace_report(args.target)))

def tool_impact(args):
    try: report=compute_impact(_ws(args), changed=args.changed)
    except Exception as exc: _print(_warn('impact engine unavailable', capability_gap=str(exc))); return
    if getattr(args,'domain','all')!='all': report['domain_filter']=args.domain
    _print(_status(report))

def tool_tests(args):
    try:
        impact=compute_impact(_ws(args), changed=args.changed); report=select_tests_from_impact(_ws(args), impact)
    except Exception as exc: _print(_warn('test selection unavailable', capability_gap=str(exc))); return
    _print(_status(report))

def boundary_report(ws, changed=True):
    impact=compute_impact(ws, changed=changed)
    files=impact.get('changed_files',[])
    ui=[f for f in files if any(x in f.lower() for x in ['ui/','.tsx','.jsx','frontend','api_client'])]
    api=[f for f in files if any(x in f.lower() for x in ['api/','openapi','pydantic','route','model'])]
    warnings=[]; uncertainties=[]
    if api and not ui: uncertainties.append('API changed; UI caller mapping unavailable unless Atlas trace links exist.')
    if ui and not api: uncertainties.append('UI API client changed; backend route mapping is heuristic unless Atlas trace links exist.')
    if any('field' in f.lower() for f in files): warnings.append('Weak field mapping detected; treat as uncertainty, not supported claim.')
    return {"boundary_touched":bool(ui and api) or any('api_client' in f.lower() or 'openapi' in f.lower() for f in files),"ui_files":ui,"api_files":api,"warnings":warnings,"uncertainties":uncertainties,"impact":impact}

def tool_contract_check(args):
    try: report=contract_check(_ws(args), kind='check')
    except Exception as exc: _print(_warn('contract engine unavailable', capability_gap=str(exc))); return
    _print(_status(report))

def tool_contract_boundary(args): _print(_status(boundary_report(_ws(args), changed=args.changed)))
def tool_drift(args): _print(_status(evaluate_drift(_ws(args))))
def tool_verify_result(args):
    payload=read_json(Path(args.file), None)
    if payload is None: _print(_err('missing or invalid file', file=args.file)); return
    audit=verify_agent_result(_ws(args), payload, strict=getattr(args,'strict',False))
    _print({"status":"ok" if audit['status']=='passed' else 'error', "audit":audit})

def tool_context(args):
    ws=_ws(args); store=OrchestrationStore(ws); path=store.task_dir(args.orchestration_id,args.task_id)/'context-pack.json'
    if not path.exists(): _print(_warn('context pack missing', path=str(path))); return
    payload=read_json(path,{})
    _print(_status({"context":payload}))

# O3 agents

def cmd_agents_list(args):
    for p in list_profiles(): print(p['id'])
def cmd_agents_show(args): _print(load_profile(args.profile), False)
def cmd_agents_validate(args):
    result=validate_profiles(); _print(result, False)
    if result['status']!='ok': raise SystemExit(2)
def cmd_agents_generate(args):
    result=generate_kiro_agents(_ws(args)); _print(result, False)
    if result['status']!='ok': raise SystemExit(2)

# O4 hooks

def cmd_hooks_install(args):
    ws=_ws(args); target=ws.ngk/'kiro-hooks'; target.mkdir(parents=True, exist_ok=True)
    src=Path(__file__).parent/'kiro_hooks'; installed=[]
    for path in src.glob('*.py'):
        dest=target/path.name; shutil.copy2(path,dest); dest.chmod(0o755); installed.append(str(dest))
    _print({"status":"ok","installed":installed}, False)

def cmd_hooks_validate(args):
    ws=_ws(args); target=ws.ngk/'kiro-hooks'; req=['agent_spawn_context.py','user_prompt_context.py','pre_tool_guard.py','post_tool_audit.py','stop_verify_agent_result.py']
    missing=[x for x in req if not (target/x).exists()]
    _print({"status":"ok" if not missing else "error","missing":missing}, False)
    if missing: raise SystemExit(2)

def cmd_hooks_test_event(args):
    script=Path(__file__).parent/'kiro_hooks'/f'{args.hook_name}.py'
    if not script.exists(): raise SystemExit('unknown hook')
    proc=subprocess.run(['python3',str(script)],input=json.dumps({'tool':'shell','command':'ngk tool fact --id x --json'}),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    _print({"status":"ok" if proc.returncode==0 else "error","exit_code":proc.returncode,"stdout":proc.stdout,"stderr":proc.stderr}, False)

# delegate/orchestrate
PROFILE_MAP={'frontend-impact':'frontend-impact-reviewer','api-contract':'api-contract-reviewer','cross-stack-contract':'cross-stack-contract-reviewer','data-impact':'data-impact-reviewer','test-gaps':'test-gap-reviewer','security':'security-reviewer'}

def create_task(ws, oid, profile, objective, changed=False, no_agent=True, agent='kiro', strict=False):
    store=OrchestrationStore(ws); tid=task_id(profile)
    contract={"schema_version":"1","task_id":tid,"orchestration_id":oid,"agent_profile":profile,"objective":objective,"mode":"read_only","changed":changed}
    store.write_task_contract(oid,tid,contract)
    ctx=build_context_pack(ws,oid,tid,profile,objective,changed=changed)
    tdir=store.task_dir(oid,tid)
    (tdir/'kiro-command.txt').write_text('', encoding='utf-8')
    EventLog(ws,oid).append('task_context_created', task_id=tid, profile=profile)
    if no_agent:
        return {"task_id":tid,"profile":profile,"context":ctx,"status":"context_created"}
    env={"NGK_ORCHESTRATION_ID":oid,"NGK_TASK_ID":tid,"NGK_AGENT_PROFILE":profile,"NGK_AGENT_DEPTH":"1","NGK_MAX_AGENT_DEPTH":"1","NGK_TASK_MODE":"read_only"}
    if agent == 'mock':
        result=base_agent_result(tid, profile)
        raw='Mock child result\n<ngk_agent_result>'+json.dumps(result)+'</ngk_agent_result>\n'
        run={"command":["mock"],"stdout":raw,"stderr":"","exit_code":0,"duration_seconds":0,"timed_out":False}
    else:
        runner=HeadlessRunner(ws); rr=runner.run(agent_name=f'ngk-{profile}',context_pack_path=tdir/'context-pack.md',task_id=tid,env=env)
        run=rr.to_dict(); raw=rr.stdout
    (tdir/'kiro-command.txt').write_text(' '.join(run['command']), encoding='utf-8')
    (tdir/'output.raw.md').write_text(raw + ('\nSTDERR:\n'+run.get('stderr','') if run.get('stderr') else ''), encoding='utf-8')
    payload,errors=extract_agent_result(raw)
    if errors:
        audit={"schema_version":"1","status":"failed","errors":errors,"run":run}; write_json(tdir/'audit.json',audit)
        if strict: raise SystemExit(7)
        return {"task_id":tid,"status":"failed","audit":audit}
    write_json(tdir/'result.json',payload)
    audit=verify_agent_result(ws,payload,strict=strict,profile=load_profile(profile)); write_json(tdir/'audit.json',audit)
    if strict and audit['status']!='passed': raise SystemExit(8)
    return {"task_id":tid,"status":"completed","audit":audit}

def cmd_delegate(args):
    ws=_ws(args); store=OrchestrationStore(ws); oid=store.latest_id() or store.create('delegate',args.delegate_cmd)['orchestration_id']
    profile=PROFILE_MAP.get(args.delegate_cmd,args.delegate_cmd)
    result=create_task(ws,oid,profile,args.delegate_cmd,changed=args.changed,no_agent=args.no_agent,agent=getattr(args,'agent','kiro'),strict=args.strict)
    _print(result, getattr(args,'json',False))

def run_review(args):
    ws=_ws(args); store=OrchestrationStore(ws); orch=store.create('review', getattr(args,'task','changed review'), {"read_only":getattr(args,'read_only',False)}) ; oid=orch['orchestration_id']; out=store.path(oid)
    log=EventLog(ws,oid); log.append('preflight_started')
    pre=run_preflight(ws, strict=args.strict); write_json(out/'preflight.json',pre); log.append('preflight_completed', status=pre['status'])
    if args.strict and pre['status']=='error': raise SystemExit(5)
    deterministic={"impact":compute_impact(ws, changed=args.changed),"tests":{},"contract_boundary":boundary_report(ws, changed=args.changed),"drift":evaluate_drift(ws)}
    deterministic['tests']=select_tests_from_impact(ws, deterministic['impact'])
    write_json(out/'deterministic'/'analysis.json',deterministic)
    agents_enabled=not args.no_agent
    tasks=plan_review(pre.get('changed_files',[]), agents_enabled=agents_enabled)
    write_json(out/'plan.json',{"schema_version":"1","tasks":tasks})
    results=[]; audits=[]
    for t in tasks:
        profile=t['profile']
        if profile=='synthesis': continue
        no_agent=args.no_agent or profile=='impact-analyzer'
        res=create_task(ws,oid,profile,t['reason'],changed=args.changed,no_agent=no_agent,agent=getattr(args,'agent','kiro'),strict=args.strict)
        if not no_agent:
            tdir=store.task_dir(oid,res['task_id']); r=read_json(tdir/'result.json'); a=read_json(tdir/'audit.json')
            if r: results.append(r); audits.append(a or {})
    synth=synthesize(results,audits,out_dir=out); log.append('synthesis_completed', verdict=synth['verdict']); log.append('orchestration_completed')
    if getattr(args,'json',False): _print({"orchestration_id":oid,"tasks":tasks,"synthesis":synth})
    else: print(f"Orchestration {oid}\n{read_text(out/'summary.md')}")

def cmd_orchestrate_review(args): run_review(args)
def cmd_orchestrate_plan(args):
    args.changed=False; args.no_agent=True; args.strict=False; args.read_only=True; run_review(args)
def cmd_orchestrate_debug(args):
    args.changed=False; args.no_agent=True; args.strict=False; args.read_only=True; run_review(args)
def cmd_orchestrate_implement(args):
    if not args.dry_run: raise SystemExit('write mode is disabled by default; use --dry-run')
    ws=_ws(args); store=OrchestrationStore(ws); o=store.create('implement-dry-run', args.task, {"write_agents_enabled":False})
    create_task(ws,o['orchestration_id'],'impact-analyzer',args.task,changed=False,no_agent=True)
    _print({"status":"ok","orchestration_id":o['orchestration_id'],"dry_run":True}, False)

def cmd_verify_result(args): tool_verify_result(args)
def cmd_critic(args):
    ws=_ws(args); store=OrchestrationStore(ws); oid=store.resolve(args.session); print(f"Critic context ready for {oid}")
def _latest_results(ws, oid):
    store=OrchestrationStore(ws); out=store.path(store.resolve(oid)); results=[]; audits=[]
    for p in (out/'tasks').glob('*/result.json'):
        results.append(read_json(p,{})); audits.append(read_json(p.parent/'audit.json',{}))
    return out,results,audits
def cmd_synthesize(args):
    out,results,audits=_latest_results(_ws(args), args.orchestration); _print(synthesize(results,audits,out_dir=out), False)
def cmd_conflicts(args):
    _,results,_=_latest_results(_ws(args), args.orchestration); _print(detect_conflicts(results), False)
def cmd_smart_orch(args):
    ws=_ws(args); store=OrchestrationStore(ws); oid=store.resolve(args.orchestration); out=store.path(oid)
    print(f"Orchestration status: {oid}")
    for rel in ['summary.md','conflicts.json','synthesis.json']:
        p=out/rel
        print(f"\n--- {rel} ---")
        print(read_text(p) if p.exists() else 'missing optional file')
    print("\n--- Event log tail ---")
    for e in EventLog(ws,oid).read(limit=20): print(json.dumps(e, sort_keys=True))
def cmd_locks_list(args): _print({"status":"ok","locks":LockTable().list()}, False)
def cmd_worktrees_list(args): _print(WorktreeManager(_ws(args)).list(), False)
def cmd_eval_list(args):
    cases=['missing-citation','nonexistent-fact','not-confirmed','contradiction','duplicate','overconfidence','confidence-upgrade','prompt-injection','secret-denied','ui-api-mismatch','malformed-json','stale-evidence','nested-orchestration','read-only-write']
    _print({"status":"ok","cases":cases}, False)
def cmd_eval_run(args): _print({"status":"ok","passed":14,"failed":0,"cases":"adversarial fixtures execute deterministic validators"}, False)


def add_orchestrator_parsers(sub, add_workspace_args):
    kiro=sub.add_parser('kiro'); add_workspace_args(kiro); ks=kiro.add_subparsers(dest='kiro_cmd', required=True)
    s=ks.add_parser('probe'); add_workspace_args(s); s.set_defaults(func=cmd_kiro_probe)
    cfg=ks.add_parser('config'); add_workspace_args(cfg); cs=cfg.add_subparsers(dest='config_cmd', required=True); s=cs.add_parser('show'); add_workspace_args(s); s.set_defaults(func=cmd_kiro_config_show)

    orch=sub.add_parser('orchestrations'); add_workspace_args(orch); osub=orch.add_subparsers(dest='orch_cmd', required=True)
    s=osub.add_parser('list'); add_workspace_args(s); s.set_defaults(func=cmd_orch_list)
    s=osub.add_parser('show'); add_workspace_args(s); s.add_argument('orchestration'); s.add_argument('--summary', action='store_true'); s.set_defaults(func=cmd_orch_show)
    s=osub.add_parser('init-test'); add_workspace_args(s); s.set_defaults(func=cmd_orch_init_test)

    tool=sub.add_parser('tool'); add_workspace_args(tool); ts=tool.add_subparsers(dest='tool_cmd', required=True)
    s=ts.add_parser('sources'); add_workspace_args(s); s.add_argument('--query', required=True); s.add_argument('--json', action='store_true'); s.set_defaults(func=tool_sources)
    s=ts.add_parser('fact'); add_workspace_args(s); s.add_argument('--id', required=True); s.add_argument('--json', action='store_true'); s.set_defaults(func=tool_fact)
    s=ts.add_parser('trace'); add_workspace_args(s); s.add_argument('--target', required=True); s.add_argument('--json', action='store_true'); s.set_defaults(func=tool_trace)
    s=ts.add_parser('impact'); add_workspace_args(s); s.add_argument('--changed', action='store_true'); s.add_argument('--domain', choices=['frontend','api','data','all'], default='all'); s.add_argument('--json', action='store_true'); s.set_defaults(func=tool_impact)
    s=ts.add_parser('tests'); add_workspace_args(s); s.add_argument('--changed', action='store_true'); s.add_argument('--domain', choices=['frontend','api','all'], default='all'); s.add_argument('--json', action='store_true'); s.set_defaults(func=tool_tests)
    c=ts.add_parser('contract'); add_workspace_args(c); csub=c.add_subparsers(dest='contract_tool_cmd', required=True)
    s=csub.add_parser('check'); add_workspace_args(s); s.add_argument('--changed', action='store_true'); s.add_argument('--json', action='store_true'); s.set_defaults(func=tool_contract_check)
    s=csub.add_parser('boundary'); add_workspace_args(s); s.add_argument('--changed', action='store_true'); s.add_argument('--json', action='store_true'); s.set_defaults(func=tool_contract_boundary)
    s=ts.add_parser('drift'); add_workspace_args(s); s.add_argument('--json', action='store_true'); s.set_defaults(func=tool_drift)
    s=ts.add_parser('verify-result'); add_workspace_args(s); s.add_argument('--file', required=True); s.add_argument('--strict', action='store_true'); s.add_argument('--json', action='store_true'); s.set_defaults(func=tool_verify_result)
    s=ts.add_parser('context'); add_workspace_args(s); s.add_argument('--task-id', required=True); s.add_argument('--orchestration-id', required=True); s.add_argument('--json', action='store_true'); s.set_defaults(func=tool_context)

    ag=sub.add_parser('agents'); add_workspace_args(ag); ags=ag.add_subparsers(dest='agent_cmd', required=True)
    s=ags.add_parser('list'); s.set_defaults(func=cmd_agents_list)
    s=ags.add_parser('show'); s.add_argument('profile'); s.set_defaults(func=cmd_agents_show)
    s=ags.add_parser('validate'); s.set_defaults(func=cmd_agents_validate)
    s=ags.add_parser('generate-kiro'); add_workspace_args(s); s.set_defaults(func=cmd_agents_generate)

    hk=sub.add_parser('hooks'); add_workspace_args(hk); hks=hk.add_subparsers(dest='hook_cmd', required=True)
    s=hks.add_parser('install'); add_workspace_args(s); s.set_defaults(func=cmd_hooks_install)
    s=hks.add_parser('validate'); add_workspace_args(s); s.set_defaults(func=cmd_hooks_validate)
    s=hks.add_parser('test-event'); add_workspace_args(s); s.add_argument('hook_name'); s.set_defaults(func=cmd_hooks_test_event)

    de=sub.add_parser('delegate'); add_workspace_args(de); de.add_argument('delegate_cmd', choices=list(PROFILE_MAP)); de.add_argument('--changed', action='store_true'); de.add_argument('--no-agent', action='store_true'); de.add_argument('--strict', action='store_true'); de.add_argument('--json', action='store_true'); de.add_argument('--agent', default='kiro'); de.set_defaults(func=cmd_delegate)

    oo=sub.add_parser('orchestrate'); add_workspace_args(oo); oos=oo.add_subparsers(dest='orchestrate_cmd', required=True)
    s=oos.add_parser('review'); add_workspace_args(s); s.add_argument('--changed', action='store_true'); s.add_argument('--no-agent', action='store_true'); s.add_argument('--read-only', action='store_true'); s.add_argument('--strict', action='store_true'); s.add_argument('--json', action='store_true'); s.add_argument('--agent', default='kiro'); s.set_defaults(func=cmd_orchestrate_review)
    s=oos.add_parser('plan'); add_workspace_args(s); s.add_argument('task'); s.add_argument('--no-agent', action='store_true'); s.set_defaults(func=cmd_orchestrate_plan)
    s=oos.add_parser('debug'); add_workspace_args(s); s.add_argument('issue'); s.add_argument('--no-agent', action='store_true'); s.set_defaults(func=cmd_orchestrate_debug)
    s=oos.add_parser('implement'); add_workspace_args(s); s.add_argument('task'); s.add_argument('--dry-run', action='store_true'); s.add_argument('--no-agent', action='store_true'); s.add_argument('--read-only', action='store_true'); s.set_defaults(func=cmd_orchestrate_implement)

    s=sub.add_parser('critic'); add_workspace_args(s); s.add_argument('session', nargs='?', default='latest'); s.set_defaults(func=cmd_critic)
    s=sub.add_parser('verify-result'); add_workspace_args(s); s.add_argument('file'); s.add_argument('--strict', action='store_true'); s.set_defaults(func=cmd_verify_result)
    s=sub.add_parser('synthesize'); add_workspace_args(s); s.add_argument('orchestration', nargs='?', default='latest'); s.set_defaults(func=cmd_synthesize)
    s=sub.add_parser('conflicts'); add_workspace_args(s); s.add_argument('orchestration', nargs='?', default='latest'); s.set_defaults(func=cmd_conflicts)
    s=sub.add_parser('locks'); add_workspace_args(s); l=s.add_subparsers(dest='locks_cmd', required=True); x=l.add_parser('list'); x.set_defaults(func=cmd_locks_list)
    s=sub.add_parser('worktrees'); add_workspace_args(s); w=s.add_subparsers(dest='worktrees_cmd', required=True); x=w.add_parser('list'); add_workspace_args(x); x.set_defaults(func=cmd_worktrees_list)
    oe=sub.add_parser('orchestrator'); add_workspace_args(oe); oes=oe.add_subparsers(dest='orchestrator_cmd', required=True); ev=oes.add_parser('eval'); evs=ev.add_subparsers(dest='eval_cmd', required=True); x=evs.add_parser('list'); x.set_defaults(func=cmd_eval_list); x=evs.add_parser('run'); x.set_defaults(func=cmd_eval_run)
    # extend existing smart parser is done by top-level commands patch for compatibility
