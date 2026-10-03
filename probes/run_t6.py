"""Bounded T6 acceptance including T2 regressions; never a model comparison."""
import argparse
import json
import os
from pathlib import Path
import unittest

def main():
    p=argparse.ArgumentParser();p.add_argument('--require-linux',action='store_true');p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True);args.output.chmod(0o700)
    os.environ['T2_OUTPUT']=str(args.output)
    suite=unittest.defaultTestLoader.loadTestsFromName('tests.test_t6.CompensationTests')
    with (args.output/'tests.log').open('w') as log: out=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    from tests.test_t2 import RESULTS
    result={'tests':out.testsRun,'failures':len(out.failures),'errors':len(out.errors),'skips':len(out.skipped),
            'cases':RESULTS,'mode':'authored controls, no inference','complete':out.wasSuccessful() and not out.skipped}
    (args.output/'report.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='cases'}))
    return 0 if result['complete'] else 1

if __name__=='__main__': raise SystemExit(main())
