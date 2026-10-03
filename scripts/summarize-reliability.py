"""Retain both post-T8 development pilot outcomes, without raw prompts or credentials."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from incidentforge.evidence import verify

rows=[]
for name in ('b2-if-001-20261003T130224Z-9bc3d1','b2-if-001-20261003T130552Z-391087'):
    root=ROOT/'runs'/name;count=verify(root)
    report=json.loads((root/'report.json').read_text())
    events=[json.loads(line) for line in (root/'events.jsonl').read_text().splitlines()]
    assert events[-1]['kind']=='report' and events[-1]['payload']==report
    started=next(e['payload'] for e in events if e['kind']=='run_started')
    validations=[]
    for p in sorted(root.glob('execution-*/independent-verification.json')):
        value=json.loads(p.read_text())
        validations.append({'verified_cases':value['verified_cases'],'archive_sha256':value['archive_sha256'],
                            'cases':value['cases']})
    rows.append({k:report[k] for k in ('run_id','variant','incident','decision','reason','edits','requested_tests',
                                     'verified_work','accounting','candidate_revision')})
    rows[-1].update(verified_events=count,source_pin_digest=hashlib.sha256(json.dumps(started['source_hashes'],sort_keys=True).encode()).hexdigest(),
        action_rejections=[e['payload']['reason'] for e in events if e['kind']=='action_rejected'],
        interpretation_recorded=any(e['kind']=='model_interpretation' for e in events),independent_development_validations=validations)
with sqlite3.connect(ROOT/'runs/t4-budget.sqlite') as db:
    settled,exposure,pending=db.execute("SELECT SUM(actual),SUM(COALESCE(actual,cap)),SUM(status='reserved') FROM calls").fetchone()
assert exposure<=200000
out={'stage':'post-T8 development','comparative_claim':False,'attempts':rows,
     'project_settled_estimate_microusd':settled,'project_exposure_microusd':exposure,'pending_calls':pending,
     'limitations':['Different successive revisions; not independent trials of one frozen model protocol.',
                    'Protected development checks only; no withheld final evaluation.',
                    'T8 remains unchanged. Causal prose is unverified.']}
folder=ROOT/'benchmarks/reliability';folder.mkdir(exist_ok=True)
(folder/'summary.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'outcomes':[r['decision'] for r in rows],'exposure_microusd':exposure,'pending_calls':pending}))
