"""Verify final evaluator transport on reference controls before campaign freeze."""
import json
from pathlib import Path
import sys
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from incidentforge.remote_backend import ContreeBackend
from incidentforge.evidence import Evidence,verify
name='t8-remote-check-'+uuid.uuid4().hex[:8];e=Evidence(ROOT/'runs'/name,name)
app=e.root/'candidate/fixture/app';app.mkdir(parents=True)
for source,target in [('common.py','common.py'),('contract.py','contract.py'),('service_v2.py','service.py')]:
    (app/target).write_bytes((ROOT/'fixture/app'/source).read_bytes())
rows=[]
for incident in ('IF-001','IF-002'):
    b=ContreeBackend(ROOT,e,incident=incident);b.count=len(rows)
    result=b.run(app.parents[1],'final_holdout')
    assert result['decision']=='accept_for_review',result
    rows.append({'incident':incident,'cases':len(result['cases']),'decision':result['decision']})
(e.root/'summary.json').write_text(json.dumps({'rows':rows,'events':verify(e.root)}))
print(json.dumps({'path':str(e.root),'rows':rows}))
