"""Three predeclared IF-002 development pilots, all outcomes retained."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]

def main():
    if sys.argv[1:]!=['--live']: raise SystemExit('Explicit --live required')
    folder=ROOT/'runs'/('t6-pilots-'+uuid.uuid4().hex[:8]);folder.mkdir()
    files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
           for part in ('src','fixture','evaluation','probes','tests','contracts','scripts')
           for p in (ROOT/part).rglob('*') if p.is_file() and p.suffix in ('.py','.md','.ps1')}
    manifest={'stage':'development','incident':'IF-002','order':['B0','B1','B2'],
              'independent_runs_per_variant':1,'created_utc':datetime.now(timezone.utc).isoformat(),
              'limits':{'model_calls':10,'executions':7,'wall_seconds':900,'edits':3,'requested_tests':2,
                        'shared_project_budget_usd':0.20},
              'files_sha256':files,'claims':'Integration/cost pilot only. Not a frozen comparison or final holdout.'}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2))
    for variant in manifest['order']:
        with sqlite3.connect(ROOT/'runs/t4-budget.sqlite') as db:
            pending=db.execute("SELECT COUNT(*) FROM calls WHERE status='reserved'").fetchone()[0]
        if pending: raise RuntimeError('Unreconciled call; stop campaign')
        before={p.name for p in (ROOT/'runs').glob('b*-if-002-*')}
        with (folder/'ledger.jsonl').open('a') as f:
            f.write(json.dumps({'variant':variant,'status':'launch_reserved'})+'\n');f.flush()
        completed=subprocess.run([sys.executable,str(ROOT/'scripts/run-t4.py'),'--live','--variant',variant,
                                  '--incident','IF-002'],capture_output=True,text=True)
        (folder/(variant+'.log')).write_text(completed.stdout+'\n'+completed.stderr)
        new=[p for p in (ROOT/'runs').glob('b*-if-002-*') if p.name not in before]
        reports=[json.loads((p/'report.json').read_text()) for p in new if (p/'report.json').exists()]
        result={'variant':variant,'exit':completed.returncode,'runs':[p.name for p in new],'reports':reports}
        with (folder/'ledger.jsonl').open('a') as f: f.write(json.dumps(result)+'\n')
        print(json.dumps(result),flush=True)
        if len(reports)!=1: raise RuntimeError('Missing/ambiguous outcome; stop campaign')
        if reports[0]['accounting']['unknown_or_pending']: raise RuntimeError('Unknown usage; stop campaign')
    print('Pilot evidence: '+str(folder),flush=True)

if __name__=='__main__': main()
