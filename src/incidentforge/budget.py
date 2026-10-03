"""Persistent project reservations. Unknown calls remain charged at their cap."""
from contextlib import closing
import sqlite3
import uuid

class BudgetExceeded(RuntimeError): pass

class Budget:
    def __init__(self,path,project_cap_microusd):
        self.path=path
        with closing(sqlite3.connect(path)) as db:
            db.execute('CREATE TABLE IF NOT EXISTS settings(cap INTEGER NOT NULL)')
            row=db.execute('SELECT cap FROM settings').fetchone()
            if row is None: db.execute('INSERT INTO settings VALUES(?)',(project_cap_microusd,))
            elif row[0]!=project_cap_microusd: raise ValueError('project cap cannot change implicitly')
            db.execute('CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY,run TEXT,cap INTEGER,actual INTEGER,status TEXT)')
            db.commit()

    def reserve(self,run_id,amount,run_cap,max_calls):
        if type(amount) is not int or amount<=0: raise ValueError('positive integer reservation required')
        with closing(sqlite3.connect(self.path,timeout=3)) as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT COUNT(*) FROM calls WHERE status='reserved'").fetchone()[0]:
                raise BudgetExceeded('unreconciled prior call; no new dispatch')
            cap=db.execute('SELECT cap FROM settings').fetchone()[0]
            used=db.execute('SELECT COALESCE(SUM(COALESCE(actual,cap)),0) FROM calls').fetchone()[0]
            run_used,count=db.execute('SELECT COALESCE(SUM(COALESCE(actual,cap)),0),COUNT(*) FROM calls WHERE run=?',(run_id,)).fetchone()
            if used+amount>cap or run_used+amount>run_cap or count>=max_calls: raise BudgetExceeded('funded call budget exhausted')
            token=uuid.uuid4().hex
            db.execute('INSERT INTO calls VALUES(?,?,?,NULL,?)',(token,run_id,amount,'reserved'));db.commit()
            return token

    def settle(self,token,actual):
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT cap,status FROM calls WHERE id=?',(token,)).fetchone()
            if not row or row[1]!='reserved': raise ValueError('invalid reservation settlement')
            if type(actual) is not int or not 0<=actual<=row[0]: raise BudgetExceeded('provider usage exceeds reservation; stop')
            db.execute("UPDATE calls SET actual=?,status='settled' WHERE id=?",(actual,token));db.commit()

    def totals(self,run_id):
        with closing(sqlite3.connect(self.path)) as db:
            rows=db.execute('SELECT cap,actual,status FROM calls WHERE run=?',(run_id,)).fetchall()
        return {'calls':len(rows),'estimated_usage_microusd':sum(r[1] or 0 for r in rows),
                'reserved_or_spent_microusd':sum(r[0] if r[1] is None else r[1] for r in rows),
                'unknown_or_pending':sum(r[2]=='reserved' for r in rows)}
