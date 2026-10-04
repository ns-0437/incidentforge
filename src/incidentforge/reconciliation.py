"""Explicit conservative accounting for terminal timed-out runs. No provider claims."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import re
import sqlite3
from .evidence import verify

def reconcile(root, run_id, *, apply=False, authority=''):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,100}',run_id): raise ValueError('invalid run ID')
    path=root/'runs'/run_id
    if path.is_symlink() or path.resolve().parent!=(root/'runs').resolve(): raise ValueError('invalid run path')
    verify(path)
    events=[json.loads(line) for line in (path/'events.jsonl').read_text().splitlines()]
    if not events or events[-1]['kind']!='report': raise ValueError('terminal report required')
    report=events[-1]['payload']
    reason='TimeoutError: Inference wall-time cap; usage unknown, no retry'
    if report.get('run_id')!=run_id or report.get('decision')!='unresolved' or report.get('reason')!=reason:
        raise ValueError('only terminal inference wall-time failures qualify')
    if not any(e['kind']=='stopped' and e['payload'].get('reason')==reason for e in events):
        raise ValueError('timeout stop evidence missing')
    reservations={e['payload']['reservation']:e['payload']['maximum_microusd'] for e in events if e['kind']=='model_reserved'}
    responses={e['payload']['reservation'] for e in events if e['kind']=='model_response'}
    ledger=root/'runs/t4-budget.sqlite'
    # Preview cannot create or change the ledger.
    with closing(sqlite3.connect(ledger.resolve().as_uri()+('?mode=rw' if apply else '?mode=ro'),uri=True)) as db:
        if apply: db.execute('BEGIN IMMEDIATE')
        rows=db.execute("SELECT id,cap,actual FROM calls WHERE run=? AND status='reserved'",(run_id,)).fetchall()
        if len(rows)!=1: raise ValueError('exactly one pending reservation required')
        token,cap,actual=rows[0]
        if actual is not None or reservations.get(token)!=cap or token in responses:
            raise ValueError('ledger does not match unanswered reservation evidence')
        settings=db.execute('SELECT cap FROM settings').fetchone()[0]
        exposure=db.execute('SELECT SUM(COALESCE(actual,cap)) FROM calls').fetchone()[0]
        receipt={'run_id':run_id,'reservation':token,'counted_microusd':cap,'actual_microusd':None,
                 'exposure_microusd':exposure,'project_cap_microusd':settings,
                 'terminal_event_sha256':events[-1]['sha256'],
                 'event_file_sha256':hashlib.sha256((path/'events.jsonl').read_bytes()).hexdigest(),
                 'from_status':'reserved','to_status':'conservative_unknown','applied':apply}
        if apply:
            if not authority.strip(): raise ValueError('explicit authority required')
            db.execute('CREATE TABLE IF NOT EXISTS timeout_reconciliations(id TEXT PRIMARY KEY, recorded_at TEXT, authority TEXT, receipt TEXT)')
            db.execute('INSERT INTO timeout_reconciliations VALUES(?,?,?,?)',
                       (token,datetime.now(timezone.utc).isoformat(),authority,json.dumps(receipt,sort_keys=True)))
            db.execute("UPDATE calls SET status='conservative_unknown' WHERE id=? AND status='reserved' AND actual IS NULL",(token,))
            if db.execute('SELECT SUM(COALESCE(actual,cap)) FROM calls').fetchone()[0]!=exposure:
                raise ValueError('exposure changed')
            db.commit()
    return receipt
