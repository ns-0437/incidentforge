"""Validate schedule infrastructure with authored controls; never tune a model here."""
import json
from pathlib import Path
import sys
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from incidentforge.backend import DockerBackend
from incidentforge.evidence import Evidence,verify
from evaluation.controls import mutate
run='t8-schedule-check-'+uuid.uuid4().hex[:8];e=Evidence(ROOT/'runs'/run,run)
app=e.root/'candidate/fixture/app';app.mkdir(parents=True);candidate=app.parents[1]
for name in ('common.py','contract.py'): (app/name).write_bytes((ROOT/'fixture/app'/name).read_bytes())
source=(ROOT/'fixture/app/service_v2.py').read_text();results=[]
for incident,controls in [('IF-001',['reference','fresh_key','always_success']),('IF-002',['reference','lost_compensation','terminal_without_release','double_release'])]:
    for control in controls:
        (app/'service.py').write_text(mutate(source,control))
        backend=DockerBackend(ROOT,e,incident=incident);backend.count=len(results)
        result=backend.run(candidate,'final_holdout')
        expected='accept_for_review' if control=='reference' else 'reject_behavior'
        assert result['decision']==expected,(incident,control,result)
        results.append({'incident':incident,'control':control,'decision':result['decision'],
                        'cases':len(result['cases']),'errors':result['errors']})
summary={'results':results,'events':verify(e.root),'model_calls':0}
(e.root/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({'path':str(e.root),**summary}))
