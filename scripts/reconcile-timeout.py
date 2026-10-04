"""Preview by default; explicit --apply keeps the full unknown reservation counted."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from incidentforge.reconciliation import reconcile

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('run_id');p.add_argument('--apply',action='store_true')
    p.add_argument('--authority',default='',help='Explicit authorization for full-reservation accounting')
    args=p.parse_args()
    try: result=reconcile(ROOT,args.run_id,apply=args.apply,authority=args.authority)
    except (ValueError,OSError) as exc: p.exit(1,str(exc)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
