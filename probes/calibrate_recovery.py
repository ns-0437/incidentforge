"""Development calibration only: reference controls, three repetitions per family."""
import json
import math
from pathlib import Path
import tempfile
import time
from fixture.harness.t2 import World
from fixture.harness.compensation import decline_restart

def main():
    rows=[]
    for family in ('IF-001','IF-002'):
        for repetition in range(3):
            with tempfile.TemporaryDirectory() as temp:
                Path(temp).chmod(0o755)
                w=World(Path(temp)/'world',fault=family=='IF-001',pause=family=='IF-001')
                try:
                    w.start()
                    if family=='IF-001':
                        w.submit()
                        if not w.dropped.wait(4): raise RuntimeError('missing committed response-loss barrier')
                        start=time.monotonic()
                        w.restart('payment')
                        startup=time.monotonic()-start
                        w.release.set()
                        observed=w.observe(timeout=4)
                        elapsed=time.monotonic()-start
                        assert observed['status']=='CONFIRMED'
                    else:
                        result=decline_restart(w,timeout=4)
                        elapsed=result['elapsed_seconds'];startup=result['startup_seconds'];observed=result['order']
                        assert observed['status']=='CANCELLED_DECLINED'
                    rows.append({'family':family,'repetition':repetition+1,'elapsed_seconds':elapsed,
                                 'startup_seconds':startup,'status':observed['status']})
                finally: w.close()
    return {'mode':'calibration','complete':True,'development_only':True,'clock':'before recovering service launch; includes readiness',
       'observations':rows,'proposed_seconds':{f:max(2,math.ceil(3*max(r['elapsed_seconds'] for r in rows if r['family']==f)))
                                            for f in ('IF-001','IF-002')},
       'limitations':['Three repetitions are not a tail latency estimate.',
                      'No final evaluator threshold has been changed.']}

if __name__=='__main__': print(json.dumps(main(),indent=2))
