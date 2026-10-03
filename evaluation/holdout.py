"""T8 schedules: withheld from model prompts, executed only after candidate freeze.
Same two defect implementations; changed payloads, restart combinations and workloads.
This is schedule generalization, not unseen-implementation generalization.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from fixture.harness.t2 import World,PORTS
from fixture.harness.compensation import decline_restart
from fixture.app.common import http
from tests.test_t2 import ContractTests
from evaluation.verifier import evaluate

VERSION='T8-schedules-v1'
BOUNDS={'IF-001':3,'IF-002':2}

def run(output,incident):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    names=['canonical_mixed_payload','contended_inventory']
    names+=['dual_restart_response_loss','cancel_after_dual_restart'] if incident=='IF-001' else ['decline_then_new_order','two_declines_with_restart']
    reports=[];errors=[]
    for name in names:
        with tempfile.TemporaryDirectory(prefix='if-final-') as temp:
            Path(temp).chmod(0o755)
            fault=name in ('dual_restart_response_loss','cancel_after_dual_restart')
            w=World(Path(temp)/'world',fault=fault,pause=fault,stock={'A':3,'B':5})
            try:
                w.start()
                if name=='canonical_mixed_payload':
                    payload={'items':[{'sku':'B','qty':2},{'sku':'A','qty':1}],'amount_cents':731,'currency':'EUR'}
                    first=w.submit('final-mixed',**payload);w.observe('final-mixed',timeout=3)
                    replay=w.submit('final-mixed',**{**payload,'items':list(reversed(payload['items']))})
                    conflict=w.submit('final-mixed',**{**payload,'amount_cents':732})
                    w.submit('final-rejected',expect='stock_reject',items=[{'sku':'B','qty':11}]);w.observe('final-rejected',timeout=3)
                    w.protocol_checks.append({'name':'canonical replay and changed amount','passed':first[0]==202 and replay[0]==200 and conflict[0]==409})
                elif name=='contended_inventory':
                    with ThreadPoolExecutor(4) as pool:
                        list(pool.map(lambda i:w.submit('final-race-'+str(i),expect='contention',items=[{'sku':'A','qty':2}],amount_cents=257),range(4)))
                    for i in range(4): w.observe('final-race-'+str(i),timeout=3)
                    w.restart('inventory')
                    w.protocol_checks.append({'name':'durable stock readable after restart','passed':http(PORTS['inventory'],'GET','/stock')[0]==200})
                elif fault:
                    oid='final-loss';w.submit(oid,items=[{'sku':'A','qty':2},{'sku':'B','qty':1}],amount_cents=913)
                    if not w.dropped.wait(4): raise RuntimeError('committed response-loss barrier missing')
                    started=time.monotonic()
                    if name=='cancel_after_dual_restart': w.cancel(oid)
                    w.restart('payment');w.restart('order');w.release.set()
                    w.observe(oid,timeout=max(.001,BOUNDS[incident]-(time.monotonic()-started)))
                    w.log({'event':'final_recovery_clock','origin':'before both service restarts','elapsed_seconds':time.monotonic()-started,'bound':BOUNDS[incident]})
                    w.submit('final-following',items=[{'sku':'B','qty':1}],amount_cents=119);w.observe('final-following',timeout=3)
                else:
                    decline_restart(w,oid='final-decline-1',timeout=BOUNDS[incident])
                    if name=='two_declines_with_restart':
                        decline_restart(w,oid='final-decline-2',timeout=BOUNDS[incident])
                    w.submit('final-after-decline',items=[{'sku':'A','qty':3},{'sku':'B','qty':2}],amount_cents=611)
                    w.observe('final-after-decline',timeout=3)
                boundary=ContractTests().boundary(w)
                destination=output/name;w.export(destination)
                sha=hashlib.sha256((destination/'manifest.json').read_bytes()).hexdigest()
                report=evaluate(destination,sha,boundary)
                report.update(case=name,boundary=boundary,manifest_sha256=sha)
                (destination/'validation.json').write_text(json.dumps(report,indent=2))
                reports.append(report)
            except Exception as exc:
                errors.append({'case':name,'error':type(exc).__name__+': '+str(exc)[:300]})
            finally: w.close()
    accepted=len(reports)==len(names) and not errors and all(r['decision']=='accept_for_review' for r in reports)
    return {'mode':'final_holdout','complete':True,'decision':'accept_for_review' if accepted else 'reject_behavior',
            'tests_run':len(names),'failures':sum(r['decision']!='accept_for_review' for r in reports),
            'errors':len(errors),'skipped':0,'case_errors':errors,'cases':reports,'schedule_version':VERSION,
            'limitations':['Four withheld schedules per family; same defect implementations as development.',
                           'Schedule repetitions do not constitute independent model trials.']}
