"""Exercise the distinguishing probe on the faulty fixture without inference."""
import json
from pathlib import Path
import sys
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from incidentforge.backend import DockerBackend
from incidentforge.evidence import Evidence,verify
from evaluation.controls import mutate
run='t5-local-'+uuid.uuid4().hex[:8]
e=Evidence(ROOT/'runs'/run,run)
c=e.root/'candidate';app=c/'fixture/app';app.mkdir(parents=True)
for name in ('common.py','contract.py'): (app/name).write_bytes((ROOT/'fixture/app'/name).read_bytes())
(app/'service.py').write_text(mutate((ROOT/'fixture/app/service_v2.py').read_text(),'fresh_key'))
result=DockerBackend(ROOT,e).run(c,'identity_probe')
assert [o['committed_charge_count'] for o in result['observations']]==[1,1,1,2],result
assert all(all(s in (200,201) for s in o['http_statuses']) for o in result['observations']),result
print(json.dumps({'result':result,'events_verified':verify(e.root),'evidence':str(e.root)},indent=2))
