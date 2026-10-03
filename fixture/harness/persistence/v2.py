"""Trusted T2 schema, transaction history and structured migrations."""
from contextlib import closing
import json
import re
import sqlite3
import uuid
from .store import Session as BaseSession, PolicyError, initialize as base_initialize


def initialize(path, service):
    base_initialize(path, service)
    with closing(sqlite3.connect(path)) as db:
        db.executescript('''
        CREATE TABLE _state_audit(seq INTEGER PRIMARY KEY, tx TEXT NOT NULL,
          key TEXT NOT NULL, value TEXT, kind TEXT NOT NULL);
        CREATE TABLE _policy_audit(seq INTEGER PRIMARY KEY, reason TEXT NOT NULL);
        CREATE TABLE _migrations(name TEXT PRIMARY KEY);
        CREATE TRIGGER _state_insert AFTER INSERT ON app_state BEGIN
          INSERT INTO _state_audit(tx,key,value,kind) VALUES(audit_tx(),NEW.key,NEW.value,'put'); END;
        CREATE TRIGGER _state_update AFTER UPDATE ON app_state BEGIN
          INSERT INTO _state_audit(tx,key,value,kind) VALUES(audit_tx(),NEW.key,NEW.value,'put'); END;
        CREATE TRIGGER _state_delete AFTER DELETE ON app_state BEGIN
          INSERT INTO _state_audit(tx,key,value,kind) VALUES(audit_tx(),OLD.key,NULL,'delete'); END;
        ''')
        if service == 'payment':
            db.executescript('''
            CREATE TABLE payment_effects(effect_id TEXT PRIMARY KEY NOT NULL,
              kind TEXT NOT NULL, intent_id TEXT NOT NULL, operation_key TEXT NOT NULL,
              amount_cents INTEGER NOT NULL, currency TEXT NOT NULL, customer_id TEXT NOT NULL,
              charge_id TEXT NOT NULL);
            CREATE TABLE _payment_audit(seq INTEGER PRIMARY KEY, effect_id TEXT NOT NULL,
              kind TEXT NOT NULL, intent_id TEXT NOT NULL, operation_key TEXT NOT NULL,
              amount_cents INTEGER NOT NULL, currency TEXT NOT NULL, customer_id TEXT NOT NULL,
              charge_id TEXT NOT NULL);
            CREATE TRIGGER _payment_insert AFTER INSERT ON payment_effects BEGIN
              INSERT INTO _payment_audit(effect_id,kind,intent_id,operation_key,amount_cents,
                currency,customer_id,charge_id) VALUES(NEW.effect_id,NEW.kind,NEW.intent_id,
                NEW.operation_key,NEW.amount_cents,NEW.currency,NEW.customer_id,NEW.charge_id); END;
            CREATE TRIGGER _payment_delete BEFORE DELETE ON payment_effects BEGIN
              SELECT RAISE(ABORT,'immutable effect'); END;
            CREATE TRIGGER _payment_update BEFORE UPDATE ON payment_effects BEGIN
              SELECT RAISE(ABORT,'immutable effect'); END;
            ''')


class Session(BaseSession):
    def __init__(self, path, service='payment', timeout=10):
        self.tx = ''
        with closing(sqlite3.connect(path)) as db:
            self.tables = {row[0] for row in db.execute('SELECT name FROM _migrations')}
        super().__init__(path, service, timeout)
        self.conn.create_function('audit_tx', 0, lambda: self.tx)

    def _authorize(self, action, arg1, arg2, database, source):
        if self._control:
            return sqlite3.SQLITE_OK
        if database not in (None, 'main'):
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_FUNCTION and arg2 == 'like':
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION and arg2 == 'audit_tx':
            return sqlite3.SQLITE_OK if source in {'_state_insert','_state_update','_state_delete'} else sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_INSERT and (
            (arg1 == '_state_audit' and source in {'_state_insert','_state_update','_state_delete'}) or
            (arg1 == '_payment_audit' and source == '_payment_insert')):
            return sqlite3.SQLITE_OK
        if arg1 == 'payment_effects' and self.service == 'payment' and action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_READ):
            return sqlite3.SQLITE_OK
        if arg1 in self.tables and action in (sqlite3.SQLITE_READ,sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE):
            return sqlite3.SQLITE_OK
        return super()._authorize(action,arg1,arg2,database,source)

    def request(self, request):
        if isinstance(request, dict) and request.get('op') == 'begin':
            self.tx = uuid.uuid4().hex
        try:
            return super().request(request)
        except PolicyError as exc:
            # Outside the failed application transaction; tampering attempts survive rollback.
            self._control = True
            try:
                self.conn.execute('INSERT INTO _policy_audit(reason) VALUES(?)', (str(exc)[:400],))
            finally:
                self._control = False
            raise


def migrate(path, operations):
    """Only typed create-table/index declarations; no candidate SQL execution."""
    def ident(value):
        if not isinstance(value,str) or not re.fullmatch(r'app_[a-z][a-z0-9_]{0,40}',value):
            raise ValueError('invalid application identifier')
        return '"' + value + '"'
    if not isinstance(operations,list) or len(operations)>16:
        raise ValueError('migration bound')
    with closing(sqlite3.connect(path)) as db:
        try:
            db.execute('BEGIN IMMEDIATE')
            for op in operations:
                if op.get('kind') == 'table' and set(op)=={'kind','name','columns'}:
                    name = ident(op['name'])
                    if not isinstance(op['columns'],dict) or not 1<=len(op['columns'])<=16:
                        raise ValueError('column bound')
                    columns=[]
                    for col,typ in op['columns'].items():
                        if typ not in {'TEXT','INTEGER','TEXT PRIMARY KEY','INTEGER PRIMARY KEY'}:
                            raise ValueError('unsupported column type')
                        columns.append(ident(col)+' '+typ)
                    db.execute('CREATE TABLE '+name+'('+','.join(columns)+')')
                    db.execute('INSERT INTO _migrations VALUES(?)',(op['name'],))
                elif op.get('kind')=='index' and set(op)=={'kind','name','table','columns','unique'}:
                    allowed={'app_state','claims'} | {r[0] for r in db.execute('SELECT name FROM _migrations')}
                    if op['table'] not in allowed or type(op['unique']) is not bool:
                        raise ValueError('protected table or invalid uniqueness')
                    cols={r[1] for r in db.execute('PRAGMA table_info("'+op['table']+'")')}
                    if not isinstance(op['columns'],list) or not op['columns'] or any(c not in cols for c in op['columns']):
                        raise ValueError('unknown columns')
                    db.execute('CREATE '+('UNIQUE ' if op['unique'] else '')+'INDEX '+ident(op['name'])+
                               ' ON "'+op['table']+'"('+','.join('"'+c+'"' for c in op['columns'])+')')
                else:
                    raise ValueError('unsupported migration')
            db.commit()
        except BaseException:
            db.rollback()
            raise
