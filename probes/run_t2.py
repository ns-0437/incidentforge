"""Local-only protected T2 development acceptance and evidence ledger."""
import argparse
from datetime import datetime,timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import sys
import time
import unittest


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--require-linux',action='store_true')
    args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    args.output.chmod(0o700)
    os.environ['T2_OUTPUT']=str(args.output)
    started=time.monotonic()
    buffer=io.StringIO()
    suite=unittest.defaultTestLoader.loadTestsFromNames(['tests.test_store','tests.test_t2_storage','tests.test_t2'])
    result=unittest.TextTestRunner(stream=buffer,verbosity=2).run(suite)
    from tests.test_t2 import RESULTS
    root=Path(__file__).resolve().parents[1]
    report={'stage':'T2','timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'status':'PASS' if result.wasSuccessful() and not result.skipped else 'FAIL',
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'skipped':[(str(t),r) for t,r in result.skipped],
        'duration_seconds':round(time.monotonic()-started,3),'python':sys.version,'platform':platform.platform(),
        'cases':[{'name':r['case'],'decision':r['decision'],'failed_properties':[p for p,v in r['properties'].items() if v['status']=='fail']} for r in RESULTS],
        'source_sha256':{str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest()
                         for folder in ('fixture','evaluation','contracts','tests','probes')
                         for f in (root/folder).rglob('*') if f.is_file() and f.suffix in {'.py','.md'}},
        'model_calls':0,'remote_calls':0,
        'limitations':['Development controls, not agent or holdout measurements.',
                       'Local Docker boundary only; ConTree remains unverified.',
                       'Finite boundary tests do not prove security against arbitrary code or kernel exploits.']}
    (args.output/'report.json').write_text(json.dumps(report,indent=2))
    (args.output/'tests.log').write_text(buffer.getvalue())
    print(buffer.getvalue())
    print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'},indent=2))
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__': raise SystemExit(main())
