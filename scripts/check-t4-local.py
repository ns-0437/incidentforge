"""No inference: exercise real Docker backend and generate reviewable public bundle."""
import json
from pathlib import Path
import sys
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from incidentforge.evidence import Evidence,verify
from incidentforge.backend import DockerBackend
from evaluation.controls import mutate

run='t4-local-'+uuid.uuid4().hex[:8]
e=Evidence(ROOT/'runs'/run,run)
c=e.root/'candidate';app=c/'fixture/app';app.mkdir(parents=True)
for name in ('common.py','contract.py'): (app/name).write_bytes((ROOT/'fixture/app'/name).read_bytes())
(app/'service.py').write_text(mutate((ROOT/'fixture/app/service_v2.py').read_text(),'fresh_key'))
(c/'CONTRACT.md').write_bytes((ROOT/'contracts/public/CONTRACT.md').read_bytes())
(c/'INCIDENT.json').write_text(json.dumps({'incident_id':'IF-001','symptom':'Duplicate charging reported following payment response loss.'}))
b=DockerBackend(ROOT,e)
before=b.run(c,'developer')
(e.root/'developer-before.json').write_text(json.dumps(before,indent=2))
# Authored reference only. This check is never presented as an agent repair.
(app/'service.py').write_bytes((ROOT/'fixture/app/service_v2.py').read_bytes())
after=b.run(c,'protected')
(e.root/'reference-validation.json').write_text(json.dumps(after,indent=2))
assert after['decision']=='accept_for_review',after
report={'status':'PASS','mode':'local authored control, no inference','model_calls':0,
        'events_verified':verify(e.root),'protected_tests':after['tests_run'],'evidence':str(e.root)}
(e.root/'report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
