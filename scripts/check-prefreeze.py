"""No inference: generated candidates on Sandbox, developer assertions on Docker."""
import json
from pathlib import Path
import sys
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from incidentforge.remote_backend import ContreeBackend,read_export
from incidentforge.backend import DockerBackend
from incidentforge.evidence import Evidence,verify
from evaluation.controls import mutate

run='prefreeze-'+uuid.uuid4().hex[:8];e=Evidence(ROOT/'runs'/run,run)
results=[]
for incident,old in [('IF-001','b2-20261003T052430Z-fc5821'),('IF-002','b0-if-002-20261003T061752Z-d2e95a')]:
    b=ContreeBackend(ROOT,e,incident=incident)
    b.count=len(results)
    if incident=='IF-001' and len(sys.argv)>1:
        recovered=Path(sys.argv[1]).resolve()
        result=read_export(recovered,'protected')
        e.event('recovered_execution',{'path':str(recovered),'result':e.artifact(result)})
    else:
        result=b.run(ROOT/'runs'/old/'candidate','protected')
    assert result['decision']=='accept_for_review',result
    results.append({'incident':incident,'candidate_run':old,'tests':result['tests_run'],'decision':result['decision']})
app=e.root/'candidate/fixture/app';app.mkdir(parents=True)
for name in ('common.py','contract.py'): (app/name).write_bytes((ROOT/'fixture/app'/name).read_bytes())
source=(ROOT/'fixture/app/service_v2.py').read_text()
candidate=app.parents[1]
(candidate/'developer-tests.json').write_text(json.dumps({'assertions':[{'name':'restart completes',
    'condition':'order_restart','path':'order.status','equals':'CANCELLED_DECLINED'}]}))
b=DockerBackend(ROOT,e,incident='IF-002');b.count=len(results)
(app/'service.py').write_text(mutate(source,'lost_compensation'))
bad=b.run(candidate,'developer');assert bad['developer_tests']['passed'] is False
(app/'service.py').write_text(source)
good=b.run(candidate,'developer');assert good['developer_tests']['passed'] is True
summary={'remote_candidates':results,'developer_assertion_negative':bad['developer_tests'],
         'developer_assertion_reference':good['developer_tests'],'events':verify(e.root),'inference_calls':0}
(e.root/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({'output':str(e.root),**summary}))
