"""Prepare an isolated IF-001 bundle and run B0 with the real Nebius adapter."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import uuid
import re
import hashlib

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from evaluation.controls import mutate
from incidentforge.evidence import Evidence,verify
from incidentforge.budget import Budget
from incidentforge.llm import Nebius
from incidentforge.backend import DockerBackend
from incidentforge.controller import Controller

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--variant',choices=['B0','B1','B2'],default='B0')
    parser.add_argument('--backend',choices=['docker','contree'],default='docker')
    parser.add_argument('--incident',choices=['IF-001','IF-002'],default='IF-001')
    parser.add_argument('--run-id',help='Controller-generated ID for local UI launches')
    args=parser.parse_args()
    if not args.live: parser.error('Use --live only with the confirmed $0.20 pilot allocation.')
    run_id=args.variant.lower()+'-'+args.incident.lower()+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6]
    if args.run_id:
        if not re.fullmatch(r'ui-[a-f0-9]{32}',args.run_id): parser.error('invalid UI run ID')
        run_id=args.run_id
    evidence=Evidence(ROOT/'runs'/run_id,run_id)
    candidate=evidence.root/'candidate'
    app=candidate/'fixture/app';app.mkdir(parents=True)
    for name in ('common.py','contract.py'): (app/name).write_bytes((ROOT/'fixture/app'/name).read_bytes())
    (app/'service.py').write_text(mutate((ROOT/'fixture/app/service_v2.py').read_text(),
                                      'fresh_key' if args.incident=='IF-001' else 'lost_compensation'))
    (candidate/'CONTRACT.md').write_bytes((ROOT/'contracts/public/CONTRACT.md').read_bytes())
    (candidate/'INCIDENT.json').write_text(json.dumps({'incident_id':args.incident,
        'symptom':('A customer reports duplicate charging after a transient payment response failure.' if args.incident=='IF-001'
                   else 'A declined order leaves stock reserved after service restart; cancellation never completes.'),
        'services':['Order','Inventory','Payment'],'visible_tests':'declared development observations'}))
    budget=Budget(ROOT/'runs/t4-budget.sqlite',200000)
    cancel=evidence.root/'CANCEL'
    from incidentforge.remote_backend import ContreeBackend
    backend=(ContreeBackend if args.backend=='contree' else DockerBackend)(ROOT,evidence,cancel,incident=args.incident)
    worker=Nebius(budget,run_id,evidence,cancel_file=cancel)
    pins={}
    for folder in ('src','fixture','evaluation','probes','tests','contracts'):
        for p in sorted((ROOT/folder).rglob('*')):
            if p.is_file() and p.suffix in {'.py','.md'}: pins[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    evidence.event('run_started',{'mode':'live','protocol':'prefreeze-development-v2','backend':args.backend,
        'source_hashes':pins,'model_budget_microusd':200000,'balance_evidence':'user screenshot $1.00, 27 days on 2026-10-03'})
    result=Controller(run_id,candidate,evidence,backend,worker,budget,cancel,variant=args.variant).run()
    result['verified_events']=verify(evidence.root)
    print(json.dumps(result,indent=2))
    print('Evidence: '+str(evidence.root))
    return 0 if result['decision']=='accept_for_review' else 1

if __name__=='__main__': raise SystemExit(main())
