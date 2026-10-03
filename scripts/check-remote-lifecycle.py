"""No inference: remote reference calibration, negative control and cancellation."""
import json
from pathlib import Path
import sys
import threading
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from incidentforge.remote_backend import ContreeBackend,read_export
from incidentforge.backend import Cancelled
from incidentforge.evidence import Evidence,verify
from evaluation.controls import mutate

run='remote-lifecycle-'+uuid.uuid4().hex[:8];e=Evidence(ROOT/'runs'/run,run)
app=e.root/'candidate/fixture/app';app.mkdir(parents=True);candidate=app.parents[1]
for name in ('common.py','contract.py'): (app/name).write_bytes((ROOT/'fixture/app'/name).read_bytes())
source=(ROOT/'fixture/app/service_v2.py').read_text();(app/'service.py').write_text(source)
b=ContreeBackend(ROOT,e,incident='IF-002')
recovered=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else None
calibration=read_export(recovered/'execution-1','calibration') if recovered else b.run(candidate,'calibration')
(e.root/'calibration.json').write_text(json.dumps(calibration,indent=2))
(app/'service.py').write_text(mutate(source,'lost_compensation'))
negative=read_export(recovered/'execution-2','protected') if recovered else b.run(candidate,'protected')
assert negative['decision']=='reject_behavior'
if recovered:
    e.event('recovered_executions',{'path':str(recovered),'calibration':e.artifact(calibration),'negative':e.artifact(negative)})
    b.count=2
done=threading.Event()
def cancel_launched():
    launch=e.root/'execution-3/launch.json'
    until=time.monotonic()+60
    while not done.wait(.1) and time.monotonic()<until:
        if launch.exists():
            b.cancel_file.write_text('lifecycle check: cancel known operation');return
worker=threading.Thread(target=cancel_launched);worker.start()
cancelled=False
try:
    b.run(candidate,'protected')
except Cancelled: cancelled=True
finally: done.set();worker.join()
assert cancelled,'cancellation did not propagate'
operation=json.loads((e.root/'execution-3/operation.json').read_text())
assert operation['status']=='CANCELLED',operation['status']
assert not (ROOT/'runs/contree-active.json').exists()
summary={'calibration':calibration,'negative_decision':negative['decision'],
         'cancellation_status':operation['status'],'events':verify(e.root),'inference_calls':0}
(e.root/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({'output':str(e.root),**summary}))
