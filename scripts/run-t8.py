"""Frozen, serial 12-slot campaign. Unknown states stop; attempts are never retried."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from evaluation.controls import mutate
from incidentforge.budget import Budget
from incidentforge.controller import Controller
from incidentforge.evidence import Evidence,verify
from incidentforge.llm import Nebius,MODEL
from incidentforge.remote_backend import ContreeBackend
from incidentforge.workspace import Workspace

def pins():
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
      for folder in ('src','fixture','evaluation','probes','tests','contracts')
      for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and p.suffix in {'.py','.md'}}

def schedule():
    rows=[]
    for repetition in (1,2):
        for incident in ('IF-001','IF-002'):
            offset=(repetition-1+(incident=='IF-002'))%3
            order=['B0','B1','B2'];order=order[offset:]+order[:offset]
            for variant in order: rows.append({'slot':len(rows)+1,'repetition':repetition,'incident':incident,'variant':variant})
    return rows

def main():
    parser=argparse.ArgumentParser();parser.add_argument('campaign');parser.add_argument('--freeze',action='store_true')
    args=parser.parse_args()
    if not args.campaign.replace('-','').isalnum(): raise ValueError('campaign name')
    campaign=ROOT/'runs'/args.campaign;manifest_path=campaign/'freeze.json'
    if args.freeze:
        campaign.mkdir(parents=True,exist_ok=False)
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        manifest={'campaign':args.campaign,'frozen_at':datetime.now(timezone.utc).isoformat(),'git_commit':commit,
          'source_hashes':pins(),'source_hash_encoding':'UTF-8 bytes with CRLF normalized to LF',
          'driver_sha256':hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
          'schedule':schedule(),'model':MODEL,'temperature':.2,'max_output_tokens':8192,
          'per_run':{'model_calls':10,'edits':3,'developer_tests':2,'agent_executions':6,'final_executions':1,'agent_seconds':900},
          'project_cap_microusd':200000,'recovery_seconds':{'IF-001':3,'IF-002':2},
          'primary_denominator':'All launched independent model runs, including errors and unknowns',
          'infrastructure_invalidity':'More than 2 of 12 launched runs with transport, unknown-usage, or missing independent verification means unreliable execution; no ranking.',
          'limitations':['Two runs per variant/family; descriptive counts only.','Same defects, distinct final schedules.',
                         'Final schedules checked against authored controls before freeze, not used for model tuning.']}
        manifest_path.write_text(json.dumps(manifest,indent=2));print(str(manifest_path));return
    manifest=json.loads(manifest_path.read_text())
    if manifest['source_hashes']!=pins() or manifest['driver_sha256']!=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest():
        raise RuntimeError('Frozen source changed; do not continue campaign')
    budget=Budget(ROOT/'runs/t4-budget.sqlite',200000)
    ledger=campaign/'launches.jsonl'
    if ledger.exists(): raise RuntimeError('Campaign already launched; no automatic resume or retries')
    for slot in manifest['schedule']:
        run_id=args.campaign+'-'+str(slot['slot']).zfill(2)
        with sqlite3.connect(budget.path) as db:
            used,pending=db.execute('SELECT COALESCE(SUM(COALESCE(actual,cap)),0),SUM(CASE WHEN actual IS NULL THEN 1 ELSE 0 END) FROM calls').fetchone()
        if pending or used+17695>200000 or (ROOT/'runs/contree-active.json').exists():
            (campaign/'stopped.json').write_text(json.dumps({'before_slot':slot['slot'],'reason':'budget or unresolved operation','used':used}));break
        with ledger.open('a') as f: f.write(json.dumps({**slot,'run_id':run_id,'launched_at':datetime.now(timezone.utc).isoformat()})+'\n');f.flush()
        e=Evidence(ROOT/'runs'/run_id,run_id);candidate=e.root/'candidate';app=candidate/'fixture/app';app.mkdir(parents=True)
        for name in ('common.py','contract.py'): (app/name).write_bytes((ROOT/'fixture/app'/name).read_bytes())
        (app/'service.py').write_text(mutate((ROOT/'fixture/app/service_v2.py').read_text(),'fresh_key' if slot['incident']=='IF-001' else 'lost_compensation'))
        (candidate/'CONTRACT.md').write_bytes((ROOT/'contracts/public/CONTRACT.md').read_bytes())
        (candidate/'INCIDENT.json').write_text(json.dumps({'incident_id':slot['incident'],'symptom':
          'A customer reports duplicate charging after a transient payment response failure.' if slot['incident']=='IF-001' else
          'A declined order leaves stock reserved after service restart; cancellation never completes.',
          'services':['Order','Inventory','Payment'],'visible_tests':'declared development observations'}))
        cancel=e.root/'CANCEL';backend=ContreeBackend(ROOT,e,cancel,incident=slot['incident'])
        # Reserve the seventh common execution slot for the withheld evaluator.
        original_run=backend.run
        def limited(path,mode):
            if backend.count>=6: raise RuntimeError('agent execution allocation exhausted')
            return original_run(path,mode)
        backend.run=limited
        e.event('run_started',{'mode':'live','campaign':args.campaign,'slot':slot,
                              'freeze_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest()})
        started=time.monotonic()
        report=Controller(run_id,candidate,e,backend,Nebius(budget,run_id,e,cancel),budget,cancel,variant=slot['variant']).run()
        final={'decision':'unresolved','reason':'No frozen candidate','cases':[]}
        final_path=None
        if report.get('candidate_revision') and not report['accounting']['unknown_or_pending']:
            final_id=run_id+'-holdout';fe=Evidence(ROOT/'runs'/final_id,final_id);fb=ContreeBackend(ROOT,fe,incident=slot['incident'])
            try:
                if Workspace(candidate).revision()!=report['candidate_revision']: raise ValueError('candidate changed before final evaluation')
                final=fb.run(candidate,'final_holdout')
                if Workspace(candidate).revision()!=report['candidate_revision']: raise ValueError('candidate changed during final evaluation')
                final_path=final_id
            except Exception as exc: final={'decision':'invalid_evaluation','reason':type(exc).__name__,'cases':[]}
            fe.event('final_result',final);verify(fe.root)
        outcome={**slot,'run_id':run_id,'development_decision':report['decision'],'final_decision':final['decision'],
                 'final_evidence':final_path,'final_result':final,'agent_report':report,'verified_events':verify(e.root),
                 'elapsed_seconds':time.monotonic()-started}
        (campaign/('slot-'+str(slot['slot']).zfill(2)+'.json')).write_text(json.dumps(outcome,indent=2))
        print(json.dumps({'slot':slot['slot'],'run':run_id,'final':final['decision'],'cost_microusd':report['accounting']['estimated_usage_microusd']}),flush=True)
    print('Campaign retained at '+str(campaign),flush=True)

if __name__=='__main__': main()
