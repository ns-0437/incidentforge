"""Check candidate adapter on IF-002 controls without inference."""
import json
from pathlib import Path
import sys
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from incidentforge.backend import DockerBackend
from incidentforge.evidence import Evidence,verify
from evaluation.controls import mutate
run='t6-adapter-'+uuid.uuid4().hex[:8];e=Evidence(ROOT/'runs'/run,run)
c=e.root/'candidate';app=c/'fixture/app';app.mkdir(parents=True)
for name in ('common.py','contract.py'): (app/name).write_bytes((ROOT/'fixture/app'/name).read_bytes())
source=(ROOT/'fixture/app/service_v2.py').read_text()
(app/'service.py').write_text(mutate(source,'lost_compensation'))
b=DockerBackend(ROOT,e,incident='IF-002')
probe=b.run(c,'compensation_probe')
assert [o.get('order',{}).get('status') for o in probe['observations'][:2]]==['CANCELLED_DECLINED','COMPENSATING'],probe
bad=b.run(c,'protected');assert bad['decision']=='reject_behavior',bad
(app/'service.py').write_text(source)
good=b.run(c,'protected');assert good['decision']=='accept_for_review',good
print(json.dumps({'evidence':str(e.root),'events':verify(e.root),'negative':bad['decision'],
                  'reference':good['decision'],'reference_tests':good['tests_run']}))
