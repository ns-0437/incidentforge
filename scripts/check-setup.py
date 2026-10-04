"""Check local live-run prerequisites without spending credits."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from incidentforge.preflight import inspect

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend',choices=['docker','contree'],default='contree')
    args=parser.parse_args()
    result=inspect(ROOT,args.backend)
    print(json.dumps(result,indent=2))
    return 0 if result['ready_for_preflighted_launch'] else 1

if __name__=='__main__': raise SystemExit(main())
