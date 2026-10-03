from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from fixture.harness.persistence.v2 import initialize,Session,migrate
from fixture.harness.persistence.store import PolicyError


class StorageV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'payment.db'
        initialize(self.path,'payment')

    def session(self):
        s=Session(self.path)
        self.addCleanup(s.close)
        s.request({'op':'begin'})
        return s

    def sql(self,s,sql,params=[]):
        return s.request({'op':'execute','sql':sql,'params':params})

    def test_effect_and_state_audits_commit_rollback_and_duplicates(self):
        s=self.session()
        for effect in ('one','two'):
            self.sql(s,'INSERT INTO payment_effects VALUES(?,?,?,?,?,?,?,?)',
                     [effect,'charge','intent','same',100,'USD','CUST-OK',''])
        self.sql(s,'INSERT INTO app_state VALUES(?,?)',['x','1'])
        s.request({'op':'commit'})
        s.request({'op':'begin'})
        self.sql(s,"UPDATE app_state SET value='2'")
        s.request({'op':'rollback'})
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(2,db.execute('SELECT COUNT(*) FROM _payment_audit').fetchone()[0])
            self.assertEqual([('1',)],db.execute('SELECT value FROM _state_audit').fetchall())

    def test_denied_tampering_rolls_back_and_records_attempt(self):
        for sql in ('SELECT * FROM _state_audit','DELETE FROM payment_effects',
                    'DROP TRIGGER _payment_insert','SELECT audit_tx()',
                    'DELETE FROM _policy_audit','PRAGMA writable_schema=ON'):
            s=self.session()
            self.sql(s,'INSERT INTO payment_effects VALUES(?,?,?,?,?,?,?,?)',
                     ['x','charge','intent','key',100,'USD','CUST-OK',''])
            with self.assertRaises(PolicyError): self.sql(s,sql)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(0,db.execute('SELECT COUNT(*) FROM _payment_audit').fetchone()[0])
            self.assertEqual(6,db.execute('SELECT COUNT(*) FROM _policy_audit').fetchone()[0])

    def test_structured_migrations_and_candidate_use(self):
        migrate(self.path,[{'kind':'table','name':'app_dedup','columns':{'app_key':'TEXT PRIMARY KEY','app_value':'TEXT'}},
                           {'kind':'index','name':'app_unique','table':'app_dedup','columns':['app_value'],'unique':True}])
        s=self.session()
        self.sql(s,'INSERT INTO app_dedup VALUES(?,?)',['key','value'])
        s.request({'op':'commit'})
        with self.assertRaises(ValueError): migrate(self.path,[{'kind':'raw','sql':'DROP TABLE charges'}])
        with self.assertRaises(ValueError): migrate(self.path,[{'kind':'index','name':'app_evil','table':'payment_effects','columns':['intent_id'],'unique':True}])

    def test_failed_unique_migration_preserves_data_and_rolls_back(self):
        s=self.session()
        for key in ('a','b'): self.sql(s,'INSERT INTO app_state VALUES(?,?)',[key,'same'])
        s.request({'op':'commit'})
        with self.assertRaises(sqlite3.IntegrityError):
            migrate(self.path,[{'kind':'table','name':'app_before','columns':{'app_id':'TEXT'}},
                {'kind':'index','name':'app_collision','table':'app_state','columns':['value'],'unique':True}])
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(2,db.execute('SELECT COUNT(*) FROM app_state').fetchone()[0])
            self.assertEqual([],db.execute("SELECT name FROM sqlite_master WHERE name='app_before'").fetchall())
