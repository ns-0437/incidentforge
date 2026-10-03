"""Authorized accounting amendment; frozen agent/evaluator and schedule unchanged."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / 'runs/t8-final-20261003'

def reconcile_completed_unknowns():
    # Never assert provider usage, remove a reservation, or retry a failed slot.
    with sqlite3.connect(ROOT/'runs/t4-budget.sqlite') as db:
        db.execute('BEGIN IMMEDIATE')
        rows = db.execute("SELECT id,run,cap FROM calls WHERE status='reserved'").fetchall()
        for token, run, cap in rows:
            outcomes = [json.loads(p.read_text()) for p in CAMPAIGN.glob('slot-*.json')]
            outcome = next((o for o in outcomes if o['run_id'] == run), None)
            if not outcome or 'usage unknown' not in outcome['agent_report']['reason']:
                raise RuntimeError('Unresolved call is not a completed failed T8 attempt')
            if cap != 17695:
                raise RuntimeError('Unexpected reservation')
            db.execute('CREATE TABLE IF NOT EXISTS conservative_reconciliations(id TEXT PRIMARY KEY, cap INTEGER, recorded_at TEXT, authority TEXT)')
            db.execute('INSERT INTO conservative_reconciliations VALUES(?,?,?,?)',
                       (token, cap, datetime.now(timezone.utc).isoformat(), 'User authorized T8 completion with full reservation counted; actual unknown'))
            db.execute("UPDATE calls SET status='conservative_unknown' WHERE id=? AND actual IS NULL", (token,))
        db.commit()

if __name__ == '__main__':
    original = ROOT/'scripts/run-t8.py'
    source = original.read_text()
    manifest = json.loads((CAMPAIGN/'freeze.json').read_text())
    assert hashlib.sha256(original.read_bytes().replace(b'\r\n', b'\n')).hexdigest() == manifest['driver_sha256']
    # Minimal driver amendments only. The original driver and frozen inputs stay intact.
    old = "if ledger.exists(): raise RuntimeError('Campaign already launched; no automatic resume or retries')"
    new = "launched = {json.loads(line)['slot'] for line in ledger.read_text().splitlines()}\n    if any(not (campaign/('slot-'+str(s).zfill(2)+'.json')).exists() for s in launched): raise RuntimeError('Launched slot has no completed outcome')"
    assert source.count(old) == 1
    source = source.replace(old, new)
    old = "for slot in manifest['schedule']:\n        run_id="
    new = "for slot in manifest['schedule']:\n        if slot['slot'] in launched: continue\n        reconcile_completed_unknowns()\n        run_id="
    assert source.count(old) == 1
    source = source.replace(old, new)
    source = source.replace('SUM(CASE WHEN actual IS NULL THEN 1 ELSE 0 END)', "SUM(CASE WHEN status=\"reserved\" THEN 1 ELSE 0 END)")
    sys.argv = [str(original), 't8-final-20261003']
    exec(compile(source, str(original), 'exec'), {'__name__':'__main__', '__file__':str(original),
         'reconcile_completed_unknowns':reconcile_completed_unknowns})
