"""Audit a terminal live rehearsal against recorded measurements and pinned source."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from incidentforge.evidence import verify
from incidentforge.grounding import facts,check_interpretation
from incidentforge.workspace import Workspace

run=ROOT/'runs'/sys.argv[1]
if run.parent!=ROOT/'runs' or not run.is_dir(): raise ValueError('run path')
count=verify(run)
events=[json.loads(line) for line in (run/'events.jsonl').read_text(encoding='utf-8').splitlines()]
def artifact(ref): return json.loads((run/'artifacts'/ref['sha256']).read_text(encoding='utf-8'))
report=json.loads((run/'report.json').read_text())
assert events[-1]['kind']=='report' and events[-1]['payload']==report
pins=next(e['payload']['source_hashes'] for e in events if e['kind']=='run_started')
changed=[name for name,sha in pins.items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha]
assert not changed,changed
records=[artifact(e['payload']['record']) for e in events if e['kind']=='record']
experiments=[r['data']['observations'] for r in records if r['kind']=='ExperimentResult' and
             r['data']['observations'].get('mode')=='compensation_probe']
interpretations=[e['payload'] for e in events if e['kind']=='model_interpretation']
grounding=None
if interpretations:
    assert len(experiments)==1 and len(interpretations)==1
    grounding=check_interpretation(interpretations[0],facts(experiments[0]))
if report['candidate_revision']:
    assert Workspace(run/'candidate').revision()==report['candidate_revision']
verifications=[]
for path in sorted(run.glob('execution-*/independent-verification.json')):
    result=json.loads(path.read_text())
    receipt=json.loads((path.parent/'receipt.json').read_text())
    assert hashlib.sha256((path.parent/'evidence.zip').read_bytes()).hexdigest()==result['archive_sha256']==receipt['sha256']
    verifications.append({'execution':path.parent.name,**result})
if report['decision']=='accept_for_review':
    assert grounding and len(verifications)==2
    assert all(v['verified_cases']==8 and v['tests_without_case_export']==0 for v in verifications)
    assert all(c['decision']=='accept_for_review' for v in verifications for c in v['cases'])
assert not (ROOT/'runs/contree-active.json').exists()
with sqlite3.connect(ROOT/'runs/t4-budget.sqlite') as db:
    cap=db.execute('SELECT cap FROM settings').fetchone()[0]
    spend,exposure,pending=db.execute("SELECT COALESCE(SUM(actual),0),COALESCE(SUM(COALESCE(actual,cap)),0),COALESCE(SUM(status='reserved'),0) FROM calls").fetchone()
assert type(cap) is int and 0<cap<=400000
assert pending==0 and exposure<=cap
summary={'run_id':run.name,'decision':report['decision'],'reason':report['reason'],
         'verified_events':count,'source_pins_unchanged':len(pins),'interpretation_gate':grounding,
         'interpretation':interpretations,'protected_verifications':verifications,
         'run_accounting':report['accounting'],'project_estimated_microusd':spend,'project_exposure_microusd':exposure,
         'project_cap_microusd':cap,'pending_calls':pending,
         'scope':'One development rehearsal; factual gate is not validation of causal reasoning or benchmark superiority.'}
(run/'rehearsal-review.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
